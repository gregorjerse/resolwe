# pylint: disable=missing-docstring
import unittest
from unittest.mock import patch

from resolwe.process.communicator import CommandError, PythonProcessCommunicator
from resolwe.process.socket_utils import Message


def reply(respond_method: str, data) -> dict:
    """Serialize the reply the listener sends to a command."""
    return getattr(Message.command("command", None), respond_method)(data).to_dict()


class PythonProcessCommunicatorTest(unittest.TestCase):
    def setUp(self):
        # Bypass the singleton wrapper to get an instance with a fake socket.
        self.communicator = PythonProcessCommunicator.klass(object())

    def call(self, name: str, received: dict, *args):
        """Call the command and return its result and the sent message."""
        with (
            patch("resolwe.process.communicator.send_data") as send_data,
            patch("resolwe.process.communicator.receive_data", return_value=received),
        ):
            result = getattr(self.communicator, name)(*args)
        return result, send_data.call_args.args[1]

    def test_ok_reply_returns_data(self):
        result, sent = self.call(
            "get_model_fields",
            reply("respond_ok", {"data": None}),
            "flow",
            "Storage",
            1,
            ["data"],
        )
        self.assertEqual(result, {"data": None})
        self.assertEqual(sent["type"], "COMMAND")
        self.assertEqual(sent["type_data"], "get_model_fields")
        self.assertEqual(sent["data"], ("flow", "Storage", 1, ["data"]))

    def test_error_reply_raises_with_received_error(self):
        error = (
            "Exception while running command handler handle_create_object: "
            "Communicator processing<->communication: no response to command."
        )
        with self.assertRaises(CommandError) as raised:
            self.call("create_object", reply("respond_error", error), "flow", "Storage")
        self.assertEqual(
            str(raised.exception), f"Command 'create_object' failed: {error}"
        )

    def test_error_status_with_ok_payload_is_not_an_error(self):
        # The listener sets the error status on the reply of a successfully
        # processed command when the data object is in the error state, for
        # instance on the process_log command that reported the error itself.
        result, _ = self.call(
            "process_log", reply("respond_error", "OK"), {"error": ["Failed."]}
        )
        self.assertEqual(result, "OK")
