import json

import lambda_function
from lambda_function import lambda_handler


def test_health_endpoint():
    """Test that the health endpoint returns a successful response."""

    event = {
        "httpMethod": "GET",
        "path": "/health",
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "healthy"}


def test_invalid_endpoint():
    """Test that an unknown endpoint returns 404."""

    event = {
        "httpMethod": "GET",
        "path": "/invalid",
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {"detail": "Endpoint not found."}


def test_missing_brand_parameter():
    """Test that missing brand query parameter returns 422."""

    event = {
        "httpMethod": "GET",
        "path": "/api/v1/phones",
        "queryStringParameters": {},
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 422
    assert json.loads(response["body"]) == {
        "detail": "Query parameter 'brand' is required."
    }


def test_health_endpoint_with_api_gateway_v2_event():
    """Test health endpoint with API Gateway HTTP API v2 event."""

    event = {
        "version": "2.0",
        "rawPath": "/health",
        "requestContext": {
            "http": {
                "method": "GET",
            }
        },
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "healthy"}


class FakePhoneLookupService:
    """Provide predictable responses for Lambda handler tests."""

    def get_manufacturers(self):
        return ["Samsung", "Apple"]

    def get_phones(self, brand):
        return [
            {
                "name": "Galaxy S24",
                "url": "https://example.com/samsung/galaxy-s24",
            }
        ]

    def get_phone_specifications(self, phone_url):
        return {"Display": "6.2 inches", "RAM": "8 GB"}


def test_get_manufacturers(monkeypatch):
    """Test that the manufacturers endpoint returns manufacturers."""

    monkeypatch.setattr(
        lambda_function,
        "_get_phone_service",
        lambda: FakePhoneLookupService(),
    )

    event = {
        "httpMethod": "GET",
        "path": "/api/v1/manufacturers",
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"manufacturers": ["Samsung", "Apple"]}


def test_get_phones(monkeypatch):
    """Test that the phones endpoint returns phones for a brand."""

    monkeypatch.setattr(
        lambda_function,
        "_get_phone_service",
        lambda: FakePhoneLookupService(),
    )

    event = {
        "httpMethod": "GET",
        "path": "/api/v1/phones",
        "queryStringParameters": {"brand": "Samsung"},
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "brand": "Samsung",
        "phones": [
            {
                "name": "Galaxy S24",
                "url": "https://example.com/samsung/galaxy-s24",
            }
        ],
    }


def test_get_phone_specifications(monkeypatch):
    """Test that the specifications endpoint returns phone specifications."""

    monkeypatch.setattr(
        lambda_function,
        "_get_phone_service",
        lambda: FakePhoneLookupService(),
    )

    event = {
        "httpMethod": "GET",
        "path": "/api/v1/phones/specifications",
        "queryStringParameters": {
            "brand": "Samsung",
            "model": "Galaxy S24",
        },
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "brand": "Samsung",
        "model": "Galaxy S24",
        "specifications": {
            "Display": "6.2 inches",
            "RAM": "8 GB",
        },
    }


def test_manufacturer_not_found(monkeypatch):
    """Test that an unknown manufacturer returns 404."""

    def raise_manufacturer_error():
        raise lambda_function.ManufacturerNotFoundError(
            "Manufacturer 'Unknown' was not found."
        )

    monkeypatch.setattr(
        lambda_function,
        "_get_phone_service",
        raise_manufacturer_error,
    )

    event = {
        "httpMethod": "GET",
        "path": "/api/v1/manufacturers",
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {
        "detail": "Manufacturer 'Unknown' was not found."
    }


def test_unexpected_error(monkeypatch):
    """Test that unexpected errors return 500."""

    def raise_unexpected_error():
        raise RuntimeError("Unexpected database failure.")

    monkeypatch.setattr(
        lambda_function,
        "_get_phone_service",
        raise_unexpected_error,
    )

    event = {
        "httpMethod": "GET",
        "path": "/api/v1/manufacturers",
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"detail": "Internal server error."}
