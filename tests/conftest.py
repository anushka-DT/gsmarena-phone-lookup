import pytest

from company_lookup.database.migrations.runner import run_migrations


@pytest.fixture
def database_path(tmp_path):
    """Provide an isolated SQLite database for each test."""
    database_file = tmp_path / "test_phone_lookup.db"

    run_migrations(database_file)

    return database_file
