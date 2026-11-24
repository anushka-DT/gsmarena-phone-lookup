"""Add cache timestamps to database tables."""

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    """Add timestamps for manufacturer and phone-list cache freshness."""
    connection.execute("ALTER TABLE manufacturers ADD COLUMN fetched_at TEXT")
    connection.execute("ALTER TABLE manufacturers ADD COLUMN phones_fetched_at TEXT")

    # Existing manufacturer records are treated as freshly cached.
    connection.execute(
        """
        UPDATE manufacturers
        SET fetched_at = CURRENT_TIMESTAMP
        """
    )

    # Preserve the age of existing phone-list data where available.
    # Manufacturers without cached phones will be refreshed on first request.
    connection.execute(
        """
        UPDATE manufacturers
        SET phones_fetched_at = (
            SELECT MAX(phones.fetched_at)
            FROM phones
            WHERE phones.manufacturer_id = manufacturers.id
        )
        """
    )


def downgrade(connection: sqlite3.Connection) -> None:
    """Remove the cache timestamp columns."""
    connection.execute("ALTER TABLE manufacturers DROP COLUMN phones_fetched_at")
    connection.execute("ALTER TABLE manufacturers DROP COLUMN fetched_at")
