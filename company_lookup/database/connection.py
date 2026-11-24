"""Manage SQLite database connections."""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path("data/phone_lookup.db")


def get_connection(
    database_path: str | Path = DATABASE_PATH,
) -> sqlite3.Connection:
    """Create and return a SQLite database connection."""
    if str(database_path) == ":memory:":
        connection = sqlite3.connect(":memory:")
    else:
        database_path = Path(database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection
