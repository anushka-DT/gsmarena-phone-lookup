import os


def get_cache_ttl_days() -> int:
    """Return the configured cache TTL in days."""
    value = os.getenv("CACHE_TTL_DAYS", "7")

    try:
        cache_ttl_days = int(value)
    except ValueError as error:
        raise ValueError("CACHE_TTL_DAYS must be a positive integer.") from error

    if cache_ttl_days < 1:
        raise ValueError("CACHE_TTL_DAYS must be at least 1.")

    return cache_ttl_days
