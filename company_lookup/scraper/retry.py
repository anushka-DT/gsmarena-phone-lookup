import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import requests

P = ParamSpec("P")
R = TypeVar("R")

MAX_ATTEMPTS = 3
INITIAL_DELAY = 1

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def retry(
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry failed HTTP operations using exponential backoff."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if initial_delay < 0:
        raise ValueError("initial_delay cannot be negative")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.HTTPError as error:
                    response = error.response

                    if (
                        response is None
                        or response.status_code not in RETRYABLE_STATUS_CODES
                        or attempt == max_attempts - 1
                    ):
                        raise

                except (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                ):
                    if attempt == max_attempts - 1:
                        raise

                time.sleep(delay)
                delay *= 2

            raise RuntimeError("Retry operation ended unexpectedly.")

        return wrapper

    return decorator
