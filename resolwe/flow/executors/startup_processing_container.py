"""Processing container startup script."""
import asyncio
import concurrent
import functools
import json
import logging
import os
import shlex
import shutil
import signal
import sys
import time
import uuid
from contextlib import suppress
from distutils.util import strtobool
from pathlib import Path

# The directory where local processing is done.
DATA_LOCAL_VOLUME = Path(os.environ.get("DATA_LOCAL_VOLUME", "/data_local"))
DATA_VOLUME = Path(os.environ.get("DATA_VOLUME", "/data"))
DATA_ALL_VOLUME = Path(os.environ.get("DATA_VOLUME", "/data_all"))
TMP_DIR = Path(os.environ.get("TMP_DIR", ".tmp"))
UPLOAD_VOLUME = Path(os.environ.get("UPLOAD_VOLUME", "/upload"))

# Basic constants.
STDOUT_LOG_PATH = DATA_VOLUME / "stdout.txt"
JSON_LOG_PATH = DATA_VOLUME / "jsonout.txt"

# Keep data settings.
KEEP_DATA = bool(strtobool(os.environ.get("FLOW_MANAGER_KEEP_DATA", "False")))

# Read configuration from environmental variables.
COMMUNICATION_CONTAINER_TIMEOUT = int(os.environ.get("CONTAINER_TIMEOUT", 300))
SOCKETS_PATH = Path(os.environ.get("SOCKETS_VOLUME", "/sockets"))
COMMUNICATION_SOCKET = SOCKETS_PATH / os.environ.get(
    "COMMUNICATION_PROCESSING_SOCKET", "_socket1.s"
)
SCRIPT_SOCKET = SOCKETS_PATH / os.environ.get("SCRIPT_SOCKET", "_socket2.s")


logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


assert sys.version_info[0] == 3, "Only Python3 is supported"
assert sys.version_info[1] >= 4, "Only Python >= 3.4 is supported"

if sys.version_info[1] == 4:
    # This is done to awoid syntax error in Python >= 3.7
    create_task = getattr(asyncio, "async")
else:
    create_task = asyncio.ensure_future


def respond(message, status, response_data):
    """Return a response."""
    if message["type"] in ["COMMAND", "EQR"]:
        response_type = "RESPONSE"
    else:
        response_type = "HBTR"
    response = {"type": response_type}
    response["type_data"] = status
    response["data"] = response_data
    response["uuid"] = message.get("uuid", uuid.uuid4().hex)
    if "sequence_number" in message:
        response["sequence_number"] = message["sequence_number"]
    response["timestamp"] = time.time()
    return response


def _copy_file_or_dir(entries):
    ## type: (Iterable[Union[str, Path]]) -> None
    """Copy file and all its references to data_volume.

    The entry is a path relative to the DATA_LOCAL_VOLUME (our working
    directory). It must be copied to the DATA_VOLUME on the shared
    filesystem.
    """
    for entry in entries:
        source = Path(entry)
        destination = DATA_VOLUME / source
        if not destination.parent.is_dir():
            destination.parent.mkdir(parents=True)

        if source.is_dir():
            if not destination.exists():
                shutil.copytree(str(source), str(destination))
            else:
                # If destination directory exists the copytree will fail.
                # In such case perform a recursive call with entries in
                # the source directory as arguments.
                #
                # TODO: fix when we support Python 3.8 and later. See
                # dirs_exist_ok argument to copytree method.
                _copy_file_or_dir(source.glob("*"))
        elif source.is_file():
            if not destination.parent.is_dir():
                destination.parent.mkdir(parents=True)
            # Use copy2 to preserve file metadata, such as file creation
            # and modification times.
            shutil.copy2(str(source), str(destination))


class ProtocolHandler:
    """Handles communication with the communication container."""

    def __init__(self, communicator):
        # type: (Communicator) -> None
        """Initialization."""
        self._script_future = None  # type: Optional[asyncio.Future] # noqa: F821
        self.return_code = 0
        self.communicator = communicator
        self._script_finishing = None
        self._response_queue = list()
        self._command_lock = asyncio.Lock()
        self._message_in_queue = asyncio.Event()
        self._command_counter = 0

    @asyncio.coroutine
    def communicate(self):
        """Listen for messages from communication container."""
        while True:
            message = yield from self.communicator.receive_data()
            if message is None:
                break
            if message["type"] == "HBT":
                logger.debug("Responding to HBT.")
                yield from self.communicator.send_data(respond(message, "OK", ""))
            elif message["type"] == "EQR":
                logger.debug("Responding to EQR.")
                yield from self.communicator.send_data(
                    respond(message, "OK", "received")
                )
            elif message["type"] == "COMMAND":
                command_name = message["type_data"]
                if command_name == "process_script":
                    if self._script_future is not None:
                        response = respond(message, "ERR", "Already processing")
                        yield from self.communicator.send_data(response)
                    else:
                        create_task(self.process_script(message))
                elif command_name == "terminate":
                    self._command_counter += 1
                    log_command = {
                        "type": "COMMAND",
                        "type_data": "process_log",
                        "data": {"info": "Processing was cancelled."},
                        "uuid": uuid.uuid4().hex,
                        "sequence_number": self._command_counter,
                        "timestamp": time.time(),
                    }
                    yield from self.communicator.send_data(log_command)
                    yield from self.communicator.receive_data()
                    response = respond(message, "OK", "")
                    yield from self.communicator.send_data(response)
                    self.terminate_script()
                    # Wait for script to do the clean-up.
                    yield from self._script_finishing.wait()
                    break
                else:
                    logger.error("Command of unknown type: %s.", message)
                    response = response(message, "ERR", "Unknown command")
                    yield from self.communicator.send_data(response)
                    break
            elif message["type"] == "RESPONSE":
                self._response_queue.append(message)
                self._message_in_queue.set()
        logger.debug("Communication with communication container stopped.")

    @asyncio.coroutine
    def send_command(self, command):
        """Send a command and return a response."""
        logger.debug("Sending command")
        with (yield from self._command_lock):
            self._command_counter += 1
            command["uuid"] = uuid.uuid4().hex
            command["sequence_number"] = self._command_counter
            command["timestamp"] = time.time()
            try:
                assert len(self._response_queue) == 0
                self._message_in_queue.clear()
                yield from self.communicator.send_data(command)
                yield from self._message_in_queue.wait()
                return self._response_queue.pop()
            except:
                logger.exception("Unknown exception in send_command.")
                raise

    @asyncio.coroutine
    def process_script(self, message):
        # type: (dict) -> ()
        """Process the given script."""
        self.return_code = 1
        self._script_future = create_task(self._execute_script(message["data"]))
        try:
            yield from self._script_future
            self.return_code = self._script_future.result()
        except asyncio.CancelledError:
            pass

        finally:
            self._script_future = None
            if KEEP_DATA:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    yield from loop.run_in_executor(
                        pool, _copy_file_or_dir, [Path("./")]
                    )

        response = respond(message, "OK", self.return_code)
        yield from self.communicator.send_data(response)

        if self._script_finishing:
            self._script_finishing.set()

    def terminate_script(self):
        """Terminate the running script."""
        if self._script_future is not None:
            logger.debug("Terminating script")
            self._script_finishing = asyncio.Event()
            self._script_future.cancel()

    @asyncio.coroutine
    def _execute_script(self, script):
        # type: (str) -> int
        """Execute given bash script.

        :returns: the return code of the script.
        """
        # Start the bash subprocess and write script to its standard input.
        logger.debug("Executing script: %s.", script)
        bash_command = "/bin/bash --login" + os.linesep

        # The following comment commands blact to not reformat the code
        # block. It must not have trailing comma due compatibility with
        # Python 3.4.

        # fmt: off
        proc = yield from asyncio.subprocess.create_subprocess_exec(
            *shlex.split(bash_command),
            limit=4 * (2 ** 20),  # 4MB buffer size for line buffering
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        # fmt: on
        assert proc.stdin is not None
        assert proc.stdout is not None
        proc.stdin.write(script.encode("utf-8"))
        proc.stdin.close()
        logger.debug("Script sent to stdin.")

        with STDOUT_LOG_PATH.open("bw") as stdout_file:
            received = yield from proc.stdout.readline()
            while received:
                stdout_file.write(received)
                received = yield from proc.stdout.readline()
                stdout_file.flush()

        yield from proc.wait()
        assert proc.returncode is not None
        logger.debug("Script finished with rc %d.", proc.returncode)
        return proc.returncode


class Communicator:
    """Simple communication class."""

    def __init__(self, reader, writer):
        """Initialization."""
        self.reader = reader
        self.writer = writer

    @asyncio.coroutine
    def send_data(self, data, size_bytes=5):
        # type: (dict, int) -> None
        """Send data over socket.

        :param s: socket to send over.
        :param data: dict that must be serialzable to JSON.
        :param size_bytes: how first many bytes in message are dedicated to the
            message size (pre-padded with zeros).
        :raises: exception on failure.
        """
        message = json.dumps(data).encode("utf-8")
        message_size = "{:0{}}".format(len(message), size_bytes).encode("utf-8")
        self.writer.write(message_size + message)
        yield from self.writer.drain()
        logger.debug("Send data: %s", data)

    @asyncio.coroutine
    def receive_data(self, size_bytes=5):
        # type: (socket.SocketType, int) -> Optional[Dict] # noqa: F821
        """Recieve data over the given socket.

        :param size_bytes: how first many bytes in message are dedicated to the
            message size (pre-padded with zeros).
        """
        with suppress(asyncio.IncompleteReadError):
            received = yield from self.reader.readexactly(size_bytes)
            message_size = int(received)
            received = yield from self.reader.readexactly(message_size)
            assert len(received) == message_size
            return json.loads(received.decode("utf-8"))


class ProcessingManager:
    """Manager class.

    It starts network servers and executes the received script.
    """

    def __init__(self):
        """Initialization."""
        self.worker_reader = None  # type: Optional[asyncio.StreamReader] # noqa: F821
        self.worker_writer = None  # type: Optional[asyncio.StreamWriter] # noqa: F821
        self.protocol_handler = None  # type: Optional[BaseProtocol] # noqa: F821
        self.worker_connected = asyncio.Event()
        self.exported_files_mapper = dict()  # type: Dict[str, str] # noqa: F821

    @asyncio.coroutine
    def _wait_for_communication_container(self, path):
        # type: (str) -> Communicator
        r"""Wait for communication container to start.

        Assumption is that the communication container is accepting connections
        and will send a single b"PING\n" when connected.

        :raises: if unable to connect for COMMUNICATOR_WAIT_TIMEOUT seconds.
        """
        for _ in range(COMMUNICATION_CONTAINER_TIMEOUT):
            try:
                reader, writer = yield from asyncio.open_unix_connection(path)
                line = (yield from reader.readline()).decode("utf-8")
                assert line.strip() == "PING"
                return Communicator(reader, writer)
            except:
                with suppress(Exception):
                    writer.close()
                    yield from writer.wait_closed()
                time.sleep(1)
        raise RuntimeError("Communication container is unreacheable.")

    @asyncio.coroutine
    def run(self):
        # type: () -> int
        """Start the main method."""
        try:
            logger.debug("Connecting to the communication container.")
            try:
                self.communicator = yield from self._wait_for_communication_container(
                    str(COMMUNICATION_SOCKET)
                )
                logger.info("Connected to the communication container.")
            except:
                logger.exception(
                    "Could not connect to the communication container for "
                    "%d seconds.",
                    COMMUNICATION_CONTAINER_TIMEOUT,
                )
                return 1

            self.protocol_handler = ProtocolHandler(self.communicator)

            # Accept network connections from the processing script.
            yield from asyncio.start_unix_server(
                self._handle_processing_script_connection,
                str(SCRIPT_SOCKET),
            )
            # Await messages from the communication controler. The command
            # stops when socket is closed or communication is stopped.
            yield from self.protocol_handler.communicate()

        except:
            logger.exception("Exception while running startup script.")
        finally:
            # Just in case connection was closed before script was finished.
            self.protocol_handler.terminate_script()
            logger.debug("Stopping processing container.")
            return self.protocol_handler.return_code

    @asyncio.coroutine
    def _handle_export_files(self, data):
        # type: (dict) -> None
        """Handle export files."""
        for file_name in data:
            unique_name = "export_" + uuid.uuid4().hex
            export_path = UPLOAD_VOLUME / unique_name
            self.exported_files_mapper[file_name] = unique_name
            shutil.move(file_name, export_path)

    @asyncio.coroutine
    def _handle_processing_script_connection(self, reader, writer):
        # type: (asyncio.StreamReader, asyncio.StreamWriter) -> None
        """Handle incoming connection from the processing script.

        The requests are just proxied to the communication container with
        the exception of the .

        Python process starts a single connection while Resolwe runtime utils
        starts a new connection for every request.
        """
        try:
            communicator = Communicator(reader, writer)
            logger.debug("Processing script connected to socket.")
            with JSON_LOG_PATH.open("at") as json_file:
                message = yield from communicator.receive_data()
                while message:
                    json_file.write(json.dumps(message) + os.linesep)
                    logger.debug("Processing script sent message: %s.", message)
                    command = message["type_data"]
                    if command == "export_files":
                        yield from self._handle_export_files(message["data"])
                        response = respond(message, "OK", "")
                    elif command == "run":
                        message["data"] = {
                            "data": message["data"],
                            "export_files_mapper": self.exported_files_mapper,
                        }
                        response = yield from self.protocol_handler.send_command(
                            message
                        )
                    else:
                        response = yield from self.protocol_handler.send_command(
                            message
                        )

                    # Terminate the script on ERROR response.
                    if response["type_data"] == "ERR":
                        logger.debug("Response with error status received, terminating")
                        self.protocol_handler.terminate_script()
                        break
                    else:
                        yield from communicator.send_data(response)
                    message = yield from communicator.receive_data()

        except (asyncio.IncompleteReadError, GeneratorExit):
            logger.info("Processing script closed connection.")
        except:
            logger.exception(
                "Unknown exception while handling processing script message."
            )
            self.protocol_handler.terminate_script()
        finally:
            writer.close()


def sig_term_handler(processing_manager):
    # type: (asyncio.Future) -> None
    """Gracefully terminate the running process."""
    logger.debug("SIG_INT received, shutting down.")
    processing_manager.protocol_handler.terminate_script()


@asyncio.coroutine
def start_processing_container():
    # type: () -> None
    """Start the processing manager and set SIGINT handler."""
    processing_manager = ProcessingManager()
    manager_future = create_task(processing_manager.run())

    asyncio.get_event_loop().add_signal_handler(
        signal.SIGINT, functools.partial(sig_term_handler, processing_manager)
    )

    # Wait for the manager task to finish.
    return (yield from manager_future)


if __name__ == "__main__":
    # Change working directory into /data_local and create .tmp directory
    # inside it.
    tmp_path = DATA_LOCAL_VOLUME / TMP_DIR
    if not tmp_path.is_dir():
        (DATA_LOCAL_VOLUME / TMP_DIR).mkdir()
    os.chdir(str(DATA_LOCAL_VOLUME))

    # Replace the code bellow with asyncio.run when we no longer have to
    # support python 3.6.
    loop = asyncio.get_event_loop()
    return_code = loop.run_until_complete(start_processing_container())
    loop.close()
    sys.exit(return_code)
