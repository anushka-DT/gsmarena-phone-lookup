import sqlite3

import pytest
import requests

from company_lookup.database.repository import PhoneRepository
from company_lookup.exceptions import ManufacturerNotFoundError
from company_lookup.services.phone_service import PhoneLookupService


class FakeScraper:
    """Provide predictable scraper responses for service tests."""

    def __init__(self):
        self.manufacturer_calls = 0
        self.phone_calls = 0
        self.specification_calls = 0

        self.manufacturers = {
            "Samsung": "https://example.com/samsung.php",
        }

        self.phones = [
            {
                "name": "Galaxy S24",
                "url": "https://example.com/galaxy-s24",
            }
        ]

        self.specifications = {
            "Network": {
                "Technology": ["GSM / HSPA / LTE / 5G"],
            }
        }

        self.manufacturer_error = None
        self.phone_error = None
        self.specification_error = None

    def get_manufacturers(self):
        self.manufacturer_calls += 1

        if self.manufacturer_error:
            raise self.manufacturer_error

        return self.manufacturers

    def get_all_phone_links(self, listing_url):
        self.phone_calls += 1

        if self.phone_error:
            raise self.phone_error

        return self.phones

    def get_phone_specifications(self, phone_url):
        self.specification_calls += 1

        if self.specification_error:
            raise self.specification_error

        return self.specifications


def create_service(scraper, database_path, cache_ttl_days=7):
    """Create a service with isolated dependencies and cache configuration."""
    repository = PhoneRepository(database_path)

    return PhoneLookupService(
        scraper=scraper,
        repository=repository,
        cache_ttl_days=cache_ttl_days,
    )


def test_get_manufacturers_returns_cached_data(database_path):
    repository = PhoneRepository(database_path)
    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_manufacturers()

    assert result == scraper.manufacturers
    assert scraper.manufacturer_calls == 0


def test_get_manufacturers_scrapes_and_saves_when_cache_is_empty(
    database_path,
):
    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_manufacturers()

    assert result == scraper.manufacturers
    assert scraper.manufacturer_calls == 1

    repository = PhoneRepository(database_path)
    assert repository.get_manufacturers() == scraper.manufacturers


def test_get_phones_returns_cached_data(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/galaxy-s24",
                }
            ]
        }
    )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phones("Samsung")

    assert result == scraper.phones
    assert scraper.phone_calls == 0


@pytest.mark.parametrize(
    "manufacturer_name",
    ["samsung", "SAMSUNG", "SaMsUnG", " samsung "],
)
def test_get_phones_accepts_case_insensitive_name_from_cache(
    database_path,
    manufacturer_name,
):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/galaxy-s24",
                }
            ]
        }
    )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phones(manufacturer_name)

    assert result == scraper.phones
    assert scraper.phone_calls == 0


def test_get_phones_scrapes_and_saves_when_cache_is_empty(database_path):
    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phones("Samsung")

    assert result == scraper.phones
    assert scraper.phone_calls == 1

    repository = PhoneRepository(database_path)

    assert repository.get_phones("Samsung") == [
        {
            "name": "Galaxy S24",
            "detail_url": "https://example.com/galaxy-s24",
        }
    ]


@pytest.mark.parametrize(
    "manufacturer_name",
    ["samsung", "SAMSUNG", "SaMsUnG"],
)
def test_get_phones_scrapes_with_case_insensitive_name(
    database_path,
    manufacturer_name,
):
    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phones(manufacturer_name)

    assert result == scraper.phones
    assert scraper.phone_calls == 1

    repository = PhoneRepository(database_path)

    assert repository.get_phones("Samsung") == [
        {
            "name": "Galaxy S24",
            "detail_url": "https://example.com/galaxy-s24",
        }
    ]


def test_get_phone_specifications_returns_cached_data(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/galaxy-s24",
                }
            ]
        }
    )

    repository.save_specifications(
        "https://example.com/galaxy-s24",
        {
            "Network": {
                "Technology": ["GSM / HSPA / LTE / 5G"],
            }
        },
    )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phone_specifications("https://example.com/galaxy-s24")

    assert result == scraper.specifications
    assert scraper.specification_calls == 0


def test_get_phone_specifications_scrapes_and_saves_when_cache_is_empty(
    database_path,
):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/galaxy-s24",
                }
            ]
        }
    )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phone_specifications("https://example.com/galaxy-s24")

    assert result == scraper.specifications
    assert scraper.specification_calls == 1

    assert (
        repository.get_specifications("https://example.com/galaxy-s24")
        == scraper.specifications
    )


def test_get_manufacturers_works_when_database_is_unavailable(tmp_path):
    scraper = FakeScraper()

    # A directory cannot be opened as a SQLite database file.
    service = create_service(scraper, tmp_path)

    result = service.get_manufacturers()

    assert result == scraper.manufacturers
    assert scraper.manufacturer_calls == 1


def test_get_phones_raises_error_for_unknown_manufacturer(database_path):
    scraper = FakeScraper()
    scraper.manufacturers = {}

    service = create_service(scraper, database_path)

    with pytest.raises(ManufacturerNotFoundError):
        service.get_phones("UnknownBrand")

    assert scraper.phone_calls == 0
    assert scraper.manufacturer_calls == 1


def test_get_manufacturers_refreshes_expired_cache(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/old-samsung"})

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE manufacturers
            SET fetched_at = datetime('now', '-8 days')
            """
        )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_manufacturers()

    assert result == scraper.manufacturers
    assert scraper.manufacturer_calls == 1


def test_get_manufacturers_returns_stale_cache_when_refresh_fails(
    database_path,
):
    repository = PhoneRepository(database_path)

    stale_manufacturers = {"Samsung": "https://example.com/old-samsung"}

    repository.save_manufacturers(stale_manufacturers)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE manufacturers
            SET fetched_at = datetime('now', '-8 days')
            """
        )

    scraper = FakeScraper()
    scraper.manufacturer_error = requests.exceptions.ConnectionError(
        "GSMArena unavailable"
    )

    service = create_service(scraper, database_path)

    result = service.get_manufacturers()

    assert result == stale_manufacturers
    assert scraper.manufacturer_calls == 1


def test_get_phones_refreshes_expired_cache(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Old Phone",
                    "detail_url": "https://example.com/old-phone",
                }
            ]
        }
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE manufacturers
            SET phones_fetched_at = datetime('now', '-8 days')
            """
        )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phones("Samsung")

    assert result == scraper.phones
    assert scraper.phone_calls == 1


def test_get_phones_returns_stale_cache_when_refresh_fails(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    stale_phones = [
        {
            "name": "Old Phone",
            "detail_url": "https://example.com/old-phone",
        }
    ]

    repository.save_phones({"Samsung": stale_phones})

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE manufacturers
            SET phones_fetched_at = datetime('now', '-8 days')
            """
        )

    scraper = FakeScraper()
    scraper.phone_error = requests.exceptions.ConnectionError("GSMArena unavailable")

    service = create_service(scraper, database_path)

    result = service.get_phones("Samsung")

    assert result == [
        {
            "name": "Old Phone",
            "url": "https://example.com/old-phone",
        }
    ]

    assert scraper.phone_calls == 1


def test_get_phones_uses_fresh_empty_cache(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})
    repository.save_phones({"Samsung": []})

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phones("Samsung")

    assert result == []
    assert scraper.phone_calls == 0


def test_get_phone_specifications_refreshes_expired_cache(database_path):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/galaxy-s24",
                }
            ]
        }
    )

    phone_url = "https://example.com/galaxy-s24"

    repository.save_specifications(
        phone_url,
        {"Network": {"Technology": ["Old specifications"]}},
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE phone_specifications
            SET fetched_at = datetime('now', '-8 days')
            """
        )

    scraper = FakeScraper()
    service = create_service(scraper, database_path)

    result = service.get_phone_specifications(phone_url)

    assert result == scraper.specifications
    assert scraper.specification_calls == 1


def test_get_phone_specifications_returns_stale_cache_when_refresh_fails(
    database_path,
):
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung.php"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/galaxy-s24",
                }
            ]
        }
    )

    phone_url = "https://example.com/galaxy-s24"

    stale_specifications = {"Network": {"Technology": ["Old specifications"]}}

    repository.save_specifications(phone_url, stale_specifications)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE phone_specifications
            SET fetched_at = datetime('now', '-8 days')
            """
        )

    scraper = FakeScraper()
    scraper.specification_error = requests.exceptions.ConnectionError(
        "GSMArena unavailable"
    )

    service = create_service(scraper, database_path)

    result = service.get_phone_specifications(phone_url)

    assert result == stale_specifications
    assert scraper.specification_calls == 1


def test_service_rejects_invalid_cache_ttl(database_path):
    scraper = FakeScraper()

    with pytest.raises(ValueError, match="cache_ttl_days"):
        create_service(scraper, database_path, cache_ttl_days=0)
