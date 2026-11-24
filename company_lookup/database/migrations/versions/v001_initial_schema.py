"""Create the initial database schema."""

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    """Create the initial application database schema."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            listing_url TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail_url TEXT NOT NULL UNIQUE,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manufacturer_id)
                REFERENCES manufacturers(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS phone_specifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id INTEGER NOT NULL UNIQUE,
            specifications_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (phone_id)
                REFERENCES phones(id)
                ON DELETE CASCADE
        )
        """
    )


def downgrade(connection: sqlite3.Connection) -> None:
    """Remove the initial application database schema."""
    connection.execute("DROP TABLE IF EXISTS phone_specifications")
    connection.execute("DROP TABLE IF EXISTS phones")
    connection.execute("DROP TABLE IF EXISTS manufacturers")
