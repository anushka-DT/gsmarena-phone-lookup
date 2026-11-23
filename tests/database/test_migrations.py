import sqlite3

from company_lookup.database.migrations.runner import run_migrations


def test_migration_creates_tables_and_records_version(tmp_path):
    database_path = tmp_path / "migration_test.db"

    run_migrations(database_path)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        versions = connection.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()

    assert {
        "manufacturers",
        "phones",
        "phone_specifications",
        "schema_migrations",
    }.issubset(tables)

    assert versions == [(1,), (2,)]


def test_running_migrations_twice_does_not_duplicate_versions(tmp_path):
    database_path = tmp_path / "migration_test.db"

    run_migrations(database_path)
    run_migrations(database_path)

    with sqlite3.connect(database_path) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()

    assert versions == [(1,), (2,)]


def test_initial_migration_preserves_existing_data(tmp_path):
    database_path = tmp_path / "existing_database.db"

    # Simulate a database created by the previous repository.
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE manufacturers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                listing_url TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            INSERT INTO manufacturers (name, listing_url)
            VALUES (?, ?)
            """,
            ("Samsung", "https://www.gsmarena.com/samsung-phones-9.php"),
        )

        connection.execute(
            """
            CREATE TABLE phones (
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
            CREATE TABLE phone_specifications (
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

    run_migrations(database_path)

    with sqlite3.connect(database_path) as connection:
        manufacturer = connection.execute("SELECT name FROM manufacturers").fetchone()

        versions = connection.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()

    assert manufacturer == ("Samsung",)
    assert versions == [(1,), (2,)]


def test_cache_migration_adds_timestamp_columns(tmp_path):
    database_path = tmp_path / "cache_migration_test.db"

    run_migrations(database_path)

    with sqlite3.connect(database_path) as connection:
        manufacturer_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(manufacturers)").fetchall()
        }

    assert "fetched_at" in manufacturer_columns
    assert "phones_fetched_at" in manufacturer_columns
