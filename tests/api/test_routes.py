import pytest
import requests
from fastapi.testclient import TestClient

from company_lookup.api.main import app
from company_lookup.api.routes import get_phone_lookup_service
from company_lookup.exceptions import ManufacturerNotFoundError


class FakePhoneLookupService:
    """Provide predictable phone lookup data for API tests."""

    def get_manufacturers(self) -> dict[str, str]:
        return {
            "Samsung": "https://example.com/samsung.php",
            "Apple": "https://example.com/apple.php",
        }

    def get_phones(self, brand: str) -> list[dict[str, str]]:
        if brand != "Samsung":
            raise ManufacturerNotFoundError(f"Manufacturer '{brand}' was not found.")

        return [
            {
                "name": "Galaxy S24",
                "url": "https://example.com/galaxy-s24",
            },
            {
                "name": "Galaxy S24 Ultra",
                "url": "https://example.com/galaxy-s24-ultra",
            },
        ]

    def get_phone_specifications(
        self,
        phone_url: str,
    ) -> dict[str, dict[str, list[str]]]:
        return {
            "Network": {
                "Technology": ["GSM / CDMA / HSPA / EVDO / LTE / 5G"],
            },
            "Display": {
                "Type": ["Dynamic LTPO AMOLED 2X"],
            },
        }


@pytest.fixture
def client():
    """Provide an API test client and clean up dependency overrides."""
    app.dependency_overrides.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def override_service(service):
    """Replace the real lookup service with a test service."""
    app.dependency_overrides[get_phone_lookup_service] = lambda: service


def test_get_manufacturers_returns_successful_response(client):
    override_service(FakePhoneLookupService())

    response = client.get("/api/v1/manufacturers")

    assert response.status_code == 200
    assert response.json() == {
        "manufacturers": {
            "Samsung": "https://example.com/samsung.php",
            "Apple": "https://example.com/apple.php",
        }
    }


def test_get_manufacturers_returns_503_when_scraper_fails(client):
    class FailingPhoneLookupService:
        """Simulate a scraper network failure."""

        def get_manufacturers(self) -> dict[str, str]:
            raise requests.ConnectionError("Connection failed")

    override_service(FailingPhoneLookupService())

    response = client.get("/api/v1/manufacturers")

    assert response.status_code == 503
    assert response.json() == {"detail": "GSMArena is temporarily unavailable."}


def test_get_phones_returns_successful_response(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones",
        params={"brand": "Samsung"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "brand": "Samsung",
        "phones": [
            {
                "name": "Galaxy S24",
                "url": "https://example.com/galaxy-s24",
            },
            {
                "name": "Galaxy S24 Ultra",
                "url": "https://example.com/galaxy-s24-ultra",
            },
        ],
    }


def test_get_phones_removes_whitespace_from_brand(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones",
        params={"brand": " Samsung "},
    )

    assert response.status_code == 200
    assert response.json()["brand"] == "Samsung"
    assert len(response.json()["phones"]) == 2


def test_get_phones_returns_404_for_unknown_manufacturer(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones",
        params={"brand": "UnknownBrand"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Manufacturer 'UnknownBrand' was not found."}


def test_get_phones_returns_503_when_scraper_fails(client):
    class FailingPhoneLookupService:
        """Simulate a network failure while retrieving phones."""

        def get_phones(self, brand: str) -> list[dict[str, str]]:
            raise requests.ConnectionError("Connection failed")

    override_service(FailingPhoneLookupService())

    response = client.get(
        "/api/v1/phones",
        params={"brand": "Samsung"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "GSMArena is temporarily unavailable."}


def test_get_phone_specifications_returns_successful_response(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params={
            "brand": "Samsung",
            "model": "Galaxy S24 Ultra",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "brand": "Samsung",
        "model": "Galaxy S24 Ultra",
        "specifications": {
            "Network": {
                "Technology": ["GSM / CDMA / HSPA / EVDO / LTE / 5G"],
            },
            "Display": {
                "Type": ["Dynamic LTPO AMOLED 2X"],
            },
        },
    }


def test_get_phone_specifications_removes_whitespace_from_inputs(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params={
            "brand": " Samsung ",
            "model": " Galaxy S24 Ultra ",
        },
    )

    assert response.status_code == 200
    assert response.json()["brand"] == "Samsung"
    assert response.json()["model"] == "Galaxy S24 Ultra"


def test_get_phone_specifications_returns_404_for_unknown_model(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params={
            "brand": "Samsung",
            "model": "Unknown Phone",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Phone model 'Unknown Phone' was not found for 'Samsung'."
    }


def test_get_phone_specifications_returns_404_for_unknown_brand(client):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params={
            "brand": "UnknownBrand",
            "model": "Galaxy S24 Ultra",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Manufacturer 'UnknownBrand' was not found."}


def test_get_phone_specifications_returns_503_when_phone_lookup_fails(client):
    class FailingPhoneLookupService:
        """Simulate a failure while retrieving the manufacturer's phones."""

        def get_phones(self, brand: str) -> list[dict[str, str]]:
            raise requests.ConnectionError("Connection failed")

    override_service(FailingPhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params={
            "brand": "Samsung",
            "model": "Galaxy S24 Ultra",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "GSMArena is temporarily unavailable."}


def test_get_phone_specifications_returns_503_when_specification_fetch_fails(
    client,
):
    class FailingPhoneLookupService:
        """Simulate a failure while fetching phone specifications."""

        def get_phones(self, brand: str) -> list[dict[str, str]]:
            return [
                {
                    "name": "Galaxy S24 Ultra",
                    "url": "https://example.com/galaxy-s24-ultra",
                }
            ]

        def get_phone_specifications(
            self,
            phone_url: str,
        ) -> dict[str, dict[str, list[str]]]:
            raise requests.Timeout("Request timed out")

    override_service(FailingPhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params={
            "brand": "Samsung",
            "model": "Galaxy S24 Ultra",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "GSMArena is temporarily unavailable."}


@pytest.mark.parametrize(
    "params",
    [
        {},
    ],
)
def test_get_phones_returns_422_when_brand_is_missing(client, params):
    override_service(FakePhoneLookupService())

    response = client.get("/api/v1/phones", params=params)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "brand"]


@pytest.mark.parametrize(
    "params, missing_parameter",
    [
        ({"brand": "Samsung"}, "model"),
        ({"model": "Galaxy S24 Ultra"}, "brand"),
        ({}, "brand"),
    ],
)
def test_get_phone_specifications_returns_422_when_required_parameter_is_missing(
    client,
    params,
    missing_parameter,
):
    override_service(FakePhoneLookupService())

    response = client.get(
        "/api/v1/phones/specifications",
        params=params,
    )

    assert response.status_code == 422
    missing_parameters = [error["loc"][-1] for error in response.json()["detail"]]
    assert missing_parameter in missing_parameters
