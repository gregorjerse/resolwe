"""Database helpers for the listener."""

import functools
import logging
import time
from typing import Callable, TypeVar

from django.conf import settings
from django.db import DatabaseError

from resolwe.utils import BraceMessage as __

logger = logging.getLogger(__name__)

# The number of attempts, overridden by ``LISTENER_DATABASE_RETRIES``. The
# value ``1`` performs no retries.
DEFAULT_DATABASE_RETRIES = 4

# The sleep (in seconds) before the first retry, doubled on every attempt.
INITIAL_RETRY_SLEEP = 1

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


def retry_database_writes(func: FunctionType) -> FunctionType:
    """Repeat the decorated write when the database aborts it.

    The decorated function must contain the entire transaction: inside an
    atomic block every attempt fails immediately.

    :raises DatabaseError: the error of the last attempt.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        attempts = max(
            1, getattr(settings, "LISTENER_DATABASE_RETRIES", DEFAULT_DATABASE_RETRIES)
        )
        sleep = INITIAL_RETRY_SLEEP
        for attempt in range(1, attempts + 1):
            try:
                return func(*args, **kwargs)
            except DatabaseError as error:
                if attempt == attempts or not is_retriable_database_error(error):
                    raise
                logger.warning(
                    __(
                        "Database error in '{}' (attempt {} of {}), retrying in {}s: {}",
                        func.__qualname__,
                        attempt,
                        attempts,
                        sleep,
                        error,
                    )
                )
                time.sleep(sleep)
                sleep *= 2

    return wrapper
