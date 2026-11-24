"""Provide database operations for manufacturers, phones, and specifications."""

import json
from contextlib import closing
from pathlib import Path

from company_lookup.database.connection import DATABASE_PATH, get_connection

PhoneSpecifications = dict[str, dict[str, str | list[str]]]
PhoneRecord = dict[str, str]


class PhoneRepository:
    """Handle SQLite operations for manufacturers, phones and specifications."""

    def __init__(self, database_path: str | Path = DATABASE_PATH) -> None:
        """Initialize the repository with a database path."""
        self.database_path = database_path

    def save_manufacturers(self, manufacturers: dict[str, str]) -> None:
        """Synchronize manufacturers and their cache timestamps."""
        if not manufacturers:
            return

        with closing(get_connection(self.database_path)) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO manufacturers (name, listing_url, fetched_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(name)
                    DO UPDATE SET
                        listing_url = excluded.listing_url,
                        fetched_at = CURRENT_TIMESTAMP
                    """,
                    manufacturers.items(),
                )

                placeholders = ", ".join("?" for _ in manufacturers)

                connection.execute(
                    f"""
                    DELETE FROM manufacturers
                    WHERE name NOT IN ({placeholders})
                    """,
                    tuple(manufacturers),
                )

    def get_manufacturers(self) -> dict[str, str]:
        """Retrieve all manufacturers and their listing URLs."""
        manufacturers, _ = self.get_manufacturers_cache()
        return manufacturers

    def get_manufacturers_cache(self) -> tuple[dict[str, str], str | None]:
        """Retrieve manufacturers and the oldest cache refresh timestamp."""
        with closing(get_connection(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT name, listing_url
                FROM manufacturers
                ORDER BY name
                """
            ).fetchall()

            timestamp_row = connection.execute(
                "SELECT MIN(fetched_at) AS fetched_at FROM manufacturers"
            ).fetchone()

        manufacturers = {row["name"]: row["listing_url"] for row in rows}

        return manufacturers, (timestamp_row["fetched_at"] if timestamp_row else None)

    def save_phones(self, phones: dict[str, list[PhoneRecord]]) -> None:
        """Replace a manufacturer's phone listing and refresh its timestamp."""
        with closing(get_connection(self.database_path)) as connection:
            with connection:
                for manufacturer_name, manufacturer_phones in phones.items():
                    manufacturer = connection.execute(
                        """
                        SELECT id
                        FROM manufacturers
                        WHERE name = ?
                        """,
                        (manufacturer_name,),
                    ).fetchone()

                    if manufacturer is None:
                        raise ValueError(
                            f"Manufacturer '{manufacturer_name}' does not exist."
                        )

                    manufacturer_id = manufacturer["id"]

                    phone_records = [
                        (
                            manufacturer_id,
                            phone["name"],
                            phone["detail_url"],
                        )
                        for phone in manufacturer_phones
                    ]

                    connection.executemany(
                        """
                        INSERT INTO phones (
                            manufacturer_id,
                            name,
                            detail_url
                        )
                        VALUES (?, ?, ?)
                        ON CONFLICT(detail_url)
                        DO UPDATE SET
                            name = excluded.name,
                            manufacturer_id = excluded.manufacturer_id
                        """,
                        phone_records,
                    )

                    current_urls = [
                        phone["detail_url"] for phone in manufacturer_phones
                    ]

                    if current_urls:
                        placeholders = ", ".join("?" for _ in current_urls)
                        connection.execute(
                            f"""
                            DELETE FROM phones
                            WHERE manufacturer_id = ?
                            AND detail_url NOT IN ({placeholders})
                            """,
                            [manufacturer_id, *current_urls],
                        )
                    else:
                        connection.execute(
                            "DELETE FROM phones WHERE manufacturer_id = ?",
                            (manufacturer_id,),
                        )

                    connection.execute(
                        """
                        UPDATE manufacturers
                        SET phones_fetched_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (manufacturer_id,),
                    )

    def get_phones(self, manufacturer_name: str) -> list[PhoneRecord]:
        """Retrieve all phones belonging to a manufacturer."""
        phones, _ = self.get_phones_cache(manufacturer_name)
        return phones

    def get_phones_cache(
        self,
        manufacturer_name: str,
    ) -> tuple[list[PhoneRecord], str | None]:
        """Retrieve a manufacturer's phones and listing refresh timestamp."""
        with closing(get_connection(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT phones.name, phones.detail_url
                FROM phones
                JOIN manufacturers
                    ON phones.manufacturer_id = manufacturers.id
                WHERE manufacturers.name = ?
                ORDER BY phones.name
                """,
                (manufacturer_name,),
            ).fetchall()

            timestamp_row = connection.execute(
                """
                SELECT phones_fetched_at
                FROM manufacturers
                WHERE name = ?
                """,
                (manufacturer_name,),
            ).fetchone()

        phones = [
            {"name": row["name"], "detail_url": row["detail_url"]} for row in rows
        ]

        return phones, (timestamp_row["phones_fetched_at"] if timestamp_row else None)

    def save_specifications(
        self,
        phone_url: str,
        specifications: PhoneSpecifications,
    ) -> None:
        """Insert or update specifications for a phone."""
        with closing(get_connection(self.database_path)) as connection:
            with connection:
                phone = connection.execute(
                    """
                    SELECT id
                    FROM phones
                    WHERE detail_url = ?
                    """,
                    (phone_url,),
                ).fetchone()

                if phone is None:
                    raise ValueError(f"Phone with URL '{phone_url}' does not exist.")

                connection.execute(
                    """
                    INSERT INTO phone_specifications (
                        phone_id,
                        specifications_json
                    )
                    VALUES (?, ?)
                    ON CONFLICT(phone_id)
                    DO UPDATE SET
                        specifications_json = excluded.specifications_json,
                        fetched_at = CURRENT_TIMESTAMP
                    """,
                    (
                        phone["id"],
                        json.dumps(specifications),
                    ),
                )

    def get_specifications(
        self,
        phone_url: str,
    ) -> PhoneSpecifications | None:
        """Retrieve specifications for a phone by its detail URL."""
        specifications, _ = self.get_specifications_cache(phone_url)
        return specifications

    def get_specifications_cache(
        self,
        phone_url: str,
    ) -> tuple[PhoneSpecifications | None, str | None]:
        """Retrieve specifications and their cache refresh timestamp."""
        with closing(get_connection(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT
                    phone_specifications.specifications_json,
                    phone_specifications.fetched_at
                FROM phone_specifications
                JOIN phones
                    ON phone_specifications.phone_id = phones.id
                WHERE phones.detail_url = ?
                """,
                (phone_url,),
            ).fetchone()

        if row is None:
            return None, None

        return json.loads(row["specifications_json"]), row["fetched_at"]
