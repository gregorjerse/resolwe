"""Database helpers for the listener."""

import functools
import logging
import random
import time
from contextlib import contextmanager
from typing import Callable, TypeVar

from django.conf import settings
from django.db import DatabaseError, connection, transaction

from resolwe.utils import BraceMessage as __

logger = logging.getLogger(__name__)

# The number of attempts of a write, overridden by
# ``LISTENER_DATABASE_WRITE_ATTEMPTS``. The value ``1`` performs no retries.
DEFAULT_DATABASE_WRITE_ATTEMPTS = 4

# The sleep (in seconds) before the first retry, doubled on every attempt and
# spread by a random factor from the range below, so the handlers that failed
# together do not retry together.
INITIAL_RETRY_SLEEP = 1
RETRY_SLEEP_SPREAD = (0.5, 1.5)

# The statement timeout (in seconds) of the repeated writes, overridden by
# ``LISTENER_DATABASE_WRITE_TIMEOUT``. Much shorter than the session timeout:
# the writes are repeated, the reads are not.
DEFAULT_DATABASE_WRITE_TIMEOUT = 30

# The errors the database raises after it aborted the transaction: nothing the
# write did was committed, so repeating it can not apply the change twice.
# Connection errors are not included, their outcome is unknown.
RETRIABLE_SQLSTATES = frozenset(
    {
        "57014",  # query_canceled: the statement timeout expired.
        "55P03",  # lock_not_available: the lock timeout expired.
        "40001",  # serialization_failure.
        "40P01",  # deadlock_detected.
    }
)

FunctionType = TypeVar("FunctionType", bound=Callable)


def is_retriable_database_error(error: BaseException) -> bool:
    """Tell whether the given database error is safe to retry."""
    # Django wraps the driver error, which carries the code: psycopg 3 in
    # 'sqlstate', psycopg 2 in 'pgcode'.
    cause = getattr(error, "__cause__", None)
    sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    return sqlstate in RETRIABLE_SQLSTATES


@contextmanager
def write_transaction():
    """Open a transaction with the write timeout applied to it.

    The timeout lasts until the end of the outermost transaction, so the block
    must not be nested in another atomic block.
    """
    timeout = getattr(
        settings, "LISTENER_DATABASE_WRITE_TIMEOUT", DEFAULT_DATABASE_WRITE_TIMEOUT
    )
    with transaction.atomic():
        if timeout and connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    [str(int(timeout * 1000))],
                )
        yield


def retry_database_writes(func: FunctionType) -> FunctionType:
    """Repeat the decorated write when the database aborts it.

    The decorated function must contain the entire transaction: inside an
    atomic block every attempt fails immediately.

    The attempts run in the thread of the command handler, so a repeated write
    occupies its handler slot for at most the number of attempts times the
    write timeout, plus the sleeps in between. The liveness probe is answered
    on the event loop before the handlers, so a listener whose handler threads
    all wait for the database still reports alive.

    :raises DatabaseError: the error of the last attempt.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        attempts = max(
            1,
            getattr(
                settings,
                "LISTENER_DATABASE_WRITE_ATTEMPTS",
                DEFAULT_DATABASE_WRITE_ATTEMPTS,
            ),
        )
        sleep = INITIAL_RETRY_SLEEP
        for attempt in range(1, attempts + 1):
            try:
                return func(*args, **kwargs)
            except DatabaseError as error:
                if attempt == attempts or not is_retriable_database_error(error):
                    raise
                pause = sleep * random.uniform(*RETRY_SLEEP_SPREAD)
                logger.warning(
                    __(
                        "Database error in '{}' (attempt {} of {}), retrying in {:.1f}s: {}",
                        func.__qualname__,
                        attempt,
                        attempts,
                        pause,
                        error,
                    )
                )
                time.sleep(pause)
                sleep *= 2

    return wrapper
