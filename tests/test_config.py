import pytest

from company_lookup.config import get_cache_ttl_days


def test_get_cache_ttl_days_returns_default(monkeypatch):
    """Use seven days when no environment variable is configured."""
    monkeypatch.delenv("CACHE_TTL_DAYS", raising=False)

    assert get_cache_ttl_days() == 7


def test_get_cache_ttl_days_reads_environment_variable(monkeypatch):
    """Read the cache duration from the environment."""
    monkeypatch.setenv("CACHE_TTL_DAYS", "14")

    assert get_cache_ttl_days() == 14


@pytest.mark.parametrize("value", ["0", "-1"])
def test_get_cache_ttl_days_rejects_non_positive_values(monkeypatch, value):
    """Reject zero and negative cache durations."""
    monkeypatch.setenv("CACHE_TTL_DAYS", value)

    with pytest.raises(ValueError):
        get_cache_ttl_days()


def test_get_cache_ttl_days_rejects_non_integer(monkeypatch):
    """Reject non-integer cache durations."""
    monkeypatch.setenv("CACHE_TTL_DAYS", "seven")

    with pytest.raises(ValueError):
        get_cache_ttl_days()
