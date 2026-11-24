import pytest

from company_lookup.database.repository import PhoneRepository


def test_save_and_get_manufacturers(database_path):
    """Verify manufacturers can be saved and retrieved."""
    repository = PhoneRepository(database_path)

    manufacturers = {
        "Samsung": "https://www.gsmarena.com/samsung-phones-9.php",
        "Apple": "https://www.gsmarena.com/apple-phones-48.php",
    }

    repository.save_manufacturers(manufacturers)

    result = repository.get_manufacturers()

    assert result == manufacturers


def test_save_manufacturers_updates_existing_entry(database_path):
    """Verify saving an existing manufacturer updates its URL."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/old-url"})

    repository.save_manufacturers({"SAMSUNG": "https://example.com/new-url"})

    result = repository.get_manufacturers()

    assert len(result) == 1
    assert result["Samsung"] == "https://example.com/new-url"


def test_save_manufacturers_removes_obsolete_entries(database_path):
    """Verify refreshing manufacturers removes obsolete entries."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers(
        {
            "Samsung": "https://example.com/samsung",
            "Apple": "https://example.com/apple",
            "Nokia": "https://example.com/nokia",
        }
    )

    repository.save_manufacturers(
        {
            "Samsung": "https://example.com/samsung-updated",
            "Apple": "https://example.com/apple",
        }
    )

    assert repository.get_manufacturers() == {
        "Samsung": "https://example.com/samsung-updated",
        "Apple": "https://example.com/apple",
    }


def test_save_manufacturers_empty_result_preserves_existing_entries(database_path):
    """Verify an empty refresh does not delete existing manufacturers."""
    repository = PhoneRepository(database_path)

    manufacturers = {
        "Samsung": "https://example.com/samsung",
        "Apple": "https://example.com/apple",
    }
    repository.save_manufacturers(manufacturers)

    repository.save_manufacturers({})

    assert repository.get_manufacturers() == manufacturers


def test_get_manufacturers_returns_empty_dictionary(database_path):
    """Verify an empty database returns an empty dictionary."""
    repository = PhoneRepository(database_path)

    result = repository.get_manufacturers()

    assert result == {}


def test_save_and_get_phones(database_path):
    """Verify phones can be saved and retrieved by manufacturer."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers(
        {"Samsung": "https://www.gsmarena.com/samsung-phones-9.php"}
    )

    phones = {
        "Samsung": [
            {
                "name": "Galaxy S24 Ultra",
                "detail_url": "https://example.com/samsung-s24-ultra",
            },
            {
                "name": "Galaxy S24",
                "detail_url": "https://example.com/samsung-s24",
            },
        ]
    }

    repository.save_phones(phones)

    result = repository.get_phones("Samsung")

    assert len(result) == 2
    assert result == sorted(phones["Samsung"], key=lambda phone: phone["name"])


def test_save_phones_updates_existing_entry(database_path):
    """Verify saving an existing phone URL updates its name."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Old Phone Name",
                    "detail_url": "https://example.com/phone",
                }
            ]
        }
    )

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Updated Phone Name",
                    "detail_url": "https://example.com/phone",
                }
            ]
        }
    )

    result = repository.get_phones("Samsung")

    assert len(result) == 1
    assert result[0]["name"] == "Updated Phone Name"


def test_save_phones_raises_error_for_unknown_manufacturer(database_path):
    """Verify phones cannot be saved for an unknown manufacturer."""
    repository = PhoneRepository(database_path)

    phones = {
        "Unknown Brand": [
            {
                "name": "Example Phone",
                "detail_url": "https://example.com/phone",
            }
        ]
    }

    with pytest.raises(ValueError, match="does not exist"):
        repository.save_phones(phones)

    assert repository.get_manufacturers() == {}


def test_get_phones_returns_empty_list(database_path):
    """Verify a manufacturer without phones returns an empty list."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})

    result = repository.get_phones("Samsung")

    assert result == []


def test_save_and_get_specifications(database_path):
    """Verify phone specifications can be saved and retrieved."""
    repository = PhoneRepository(database_path)
    phone_url = "https://example.com/samsung-s24"

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": phone_url,
                }
            ]
        }
    )

    specifications = {
        "Network": {"Technology": "GSM / HSPA / LTE / 5G"},
        "Display": {"Type": "AMOLED", "Size": "6.2 inches"},
    }

    repository.save_specifications(phone_url, specifications)

    result = repository.get_specifications(phone_url)

    assert result == specifications


def test_save_specifications_updates_existing_entry(database_path):
    """Verify saving specifications again updates the existing record."""
    repository = PhoneRepository(database_path)
    phone_url = "https://example.com/samsung-s24"

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": phone_url,
                }
            ]
        }
    )

    repository.save_specifications(
        phone_url,
        {"Display": {"Type": "AMOLED"}},
    )

    updated_specifications = {
        "Display": {"Type": "Dynamic AMOLED 2X", "Size": "6.2 inches"}
    }

    repository.save_specifications(
        phone_url,
        updated_specifications,
    )

    result = repository.get_specifications(phone_url)

    assert result == updated_specifications


def test_save_specifications_raises_error_for_unknown_phone(database_path):
    """Verify specifications cannot be saved for an unknown phone."""
    repository = PhoneRepository(database_path)

    with pytest.raises(ValueError, match="does not exist"):
        repository.save_specifications(
            "https://example.com/unknown-phone",
            {"Display": {"Type": "AMOLED"}},
        )


def test_get_specifications_returns_none_when_not_found(database_path):
    """Verify missing phone specifications return None."""
    repository = PhoneRepository(database_path)

    result = repository.get_specifications("https://example.com/unknown-phone")

    assert result is None


def test_get_manufacturers_cache_returns_timestamp(database_path):
    """Verify manufacturer cache includes its refresh timestamp."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})

    manufacturers, fetched_at = repository.get_manufacturers_cache()

    assert manufacturers == {"Samsung": "https://example.com/samsung"}
    assert fetched_at is not None


def test_get_phones_cache_tracks_empty_listing(database_path):
    """Verify an empty phone listing can still have a cache timestamp."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})
    repository.save_phones({"Samsung": []})

    phones, fetched_at = repository.get_phones_cache("Samsung")

    assert phones == []
    assert fetched_at is not None


def test_save_phones_removes_obsolete_records_and_preserves_existing_specs(
    database_path,
):
    """Verify refresh removes obsolete phones without losing retained specs."""
    repository = PhoneRepository(database_path)

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/s24",
                },
                {
                    "name": "Galaxy S23",
                    "detail_url": "https://example.com/s23",
                },
            ]
        }
    )

    repository.save_specifications(
        "https://example.com/s24",
        {"Display": {"Type": ["AMOLED"]}},
    )
    repository.save_specifications(
        "https://example.com/s23",
        {"Display": {"Type": ["AMOLED"]}},
    )

    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": "https://example.com/s24",
                }
            ]
        }
    )

    phones = repository.get_phones("Samsung")

    assert phones == [
        {
            "name": "Galaxy S24",
            "detail_url": "https://example.com/s24",
        }
    ]

    assert repository.get_specifications("https://example.com/s24") == {
        "Display": {"Type": ["AMOLED"]}
    }

    assert repository.get_specifications("https://example.com/s23") is None


def test_get_specifications_cache_returns_timestamp(database_path):
    """Verify specification cache includes its refresh timestamp."""
    repository = PhoneRepository(database_path)
    phone_url = "https://example.com/s24"

    repository.save_manufacturers({"Samsung": "https://example.com/samsung"})
    repository.save_phones(
        {
            "Samsung": [
                {
                    "name": "Galaxy S24",
                    "detail_url": phone_url,
                }
            ]
        }
    )

    specifications = {"Display": {"Type": ["AMOLED"]}}
    repository.save_specifications(phone_url, specifications)

    cached_specs, fetched_at = repository.get_specifications_cache(phone_url)

    assert cached_specs == specifications
    assert fetched_at is not None
