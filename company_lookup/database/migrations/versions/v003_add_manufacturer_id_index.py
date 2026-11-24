"""Add an index for manufacturer-based phone lookups."""

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    """Add an index for phone lookups by manufacturer."""
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_phones_manufacturer_id
        ON phones(manufacturer_id)
        """
    )


def downgrade(connection: sqlite3.Connection) -> None:
    """Remove the manufacturer ID index."""
    connection.execute("DROP INDEX IF EXISTS idx_phones_manufacturer_id")
