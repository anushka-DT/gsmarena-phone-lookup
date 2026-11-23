from dataclasses import FrozenInstanceError

import pytest

from company_lookup.models import Manufacturer, Phone


def test_manufacturer_creation():
    manufacturer = Manufacturer(
        name="Samsung",
        listing_url="https://www.gsmarena.com/samsung-phones-9.php",
    )

    assert manufacturer.name == "Samsung"
    assert manufacturer.listing_url == ("https://www.gsmarena.com/samsung-phones-9.php")


def test_phone_creation():
    phone = Phone(
        name="Galaxy S24",
        url="https://www.gsmarena.com/samsung_galaxy_s24-12773.php",
    )

    assert phone.name == "Galaxy S24"
    assert phone.url == ("https://www.gsmarena.com/samsung_galaxy_s24-12773.php")


def test_dataclass_objects_with_same_values_are_equal():
    first = Phone(
        name="Galaxy S24",
        url="https://www.gsmarena.com/samsung_galaxy_s24-12773.php",
    )

    second = Phone(
        name="Galaxy S24",
        url="https://www.gsmarena.com/samsung_galaxy_s24-12773.php",
    )

    assert first == second


def test_manufacturer_is_immutable():
    manufacturer = Manufacturer(
        name="Samsung",
        listing_url="https://www.gsmarena.com/samsung-phones-9.php",
    )

    with pytest.raises(FrozenInstanceError):
        manufacturer.name = "Apple"


def test_phone_is_immutable():
    phone = Phone(
        name="Galaxy S24",
        url="https://www.gsmarena.com/samsung_galaxy_s24-12773.php",
    )

    with pytest.raises(FrozenInstanceError):
        phone.name = "iPhone 16"
