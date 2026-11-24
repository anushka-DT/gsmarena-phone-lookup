"""Manage database migration execution."""

from contextlib import closing
from pathlib import Path

from company_lookup.database.connection import get_connection
from company_lookup.database.migrations.versions.v001_initial_schema import (
    upgrade as create_initial_schema,
)
from company_lookup.database.migrations.versions.v002_add_cache_timestamps import (
    upgrade as add_cache_timestamps,
)
from company_lookup.database.migrations.versions.v003_add_manufacturer_id_index import (
    upgrade as add_manufacturer_id_index,
)


def run_migrations(database_path: str | Path) -> None:
    """Apply all pending database migrations in order."""
    with closing(get_connection(database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            applied_versions = {
                row["version"]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }

            migrations = [
                (1, create_initial_schema),
                (2, add_cache_timestamps),
                (3, add_manufacturer_id_index),
            ]

            for version, migration in migrations:
                if version in applied_versions:
                    continue

                migration(connection)

                connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (version,),
                )
