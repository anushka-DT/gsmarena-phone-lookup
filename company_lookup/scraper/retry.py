import random
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import requests

P = ParamSpec("P")
R = TypeVar("R")

MAX_ATTEMPTS = 3
INITIAL_DELAY = 1.0
JITTER_FACTOR = 0.5

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


def _should_retry(error: Exception) -> bool:
    """Check whether an exception represents a temporary failure."""
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    if isinstance(error, requests.exceptions.HTTPError):
        response = error.response
        return response is not None and response.status_code in RETRYABLE_STATUS_CODES

    return False


def _calculate_delay(delay: float) -> float:
    """Calculate exponential backoff delay with random jitter."""
    return random.uniform(
        delay * (1 - JITTER_FACTOR),
        delay * (1 + JITTER_FACTOR),
    )


def retry(
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a function after temporary HTTP or network failures."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if initial_delay < 0:
        raise ValueError("initial_delay cannot be negative")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = initial_delay
            attempt = 0

            while True:
                attempt += 1

                try:
                    return func(*args, **kwargs)

                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                ) as error:
                    if attempt >= max_attempts or not _should_retry(error):
                        raise

                    time.sleep(_calculate_delay(delay))
                    delay *= 2

        return wrapper

    return decorator
