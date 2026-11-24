"""Handle API Gateway requests for the GSMArena phone lookup service."""

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import requests

from company_lookup.config import get_cache_ttl_days
from company_lookup.database.migrations.runner import run_migrations
from company_lookup.exceptions import ManufacturerNotFoundError
from company_lookup.services.phone_service import PhoneLookupService

logger = logging.getLogger(__name__)

DATABASE_PATH = Path("/tmp/phone_lookup.db")

_phone_service: PhoneLookupService | None = None


def _get_phone_service() -> PhoneLookupService:
    """Create the phone lookup service once per Lambda execution environment."""
    global _phone_service

    if _phone_service is None:
        run_migrations(DATABASE_PATH)

        _phone_service = PhoneLookupService(
            database_path=DATABASE_PATH,
            cache_ttl_days=get_cache_ttl_days(),
        )

    return _phone_service


def _get_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build an API Gateway Lambda proxy response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def _get_request_details(
    event: dict[str, Any],
) -> tuple[str, str, dict[str, str]]:
    """Extract the HTTP method, path, and query parameters."""

    # API Gateway REST API (v1) and HTTP API (v2).
    method = event.get("httpMethod") or event.get("requestContext", {}).get(
        "http", {}
    ).get("method", "")

    path = event.get("path") or event.get("rawPath", "")

    query_parameters = event.get("queryStringParameters") or {}

    # API Gateway v2 can provide query parameters in rawQueryString.
    if not query_parameters and event.get("rawQueryString"):
        parsed = parse_qs(event["rawQueryString"])
        query_parameters = {key: values[0] for key, values in parsed.items()}

    return method, path, query_parameters


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Handle incoming API Gateway requests."""

    try:
        method, path, query_parameters = _get_request_details(event)

        # Health endpoint.
        if method == "GET" and path == "/health":
            return _get_response(200, {"status": "healthy"})

        service = _get_phone_service()

        # Get all manufacturers.
        if method == "GET" and path == "/api/v1/manufacturers":
            manufacturers = service.get_manufacturers()

            return _get_response(
                200,
                {"manufacturers": manufacturers},
            )

        # Get phones belonging to a manufacturer.
        if method == "GET" and path == "/api/v1/phones":
            brand = (query_parameters.get("brand") or "").strip()

            if not brand:
                return _get_response(
                    422,
                    {"detail": "Query parameter 'brand' is required."},
                )

            phones = service.get_phones(brand)

            return _get_response(
                200,
                {"brand": brand, "phones": phones},
            )

        # Get specifications for a particular phone.
        if method == "GET" and path == "/api/v1/phones/specifications":
            brand = (query_parameters.get("brand") or "").strip()
            model = (query_parameters.get("model") or "").strip()

            if not brand or not model:
                return _get_response(
                    422,
                    {"detail": ("Query parameters 'brand' and 'model' are required.")},
                )

            phones = service.get_phones(brand)

            phone = next(
                (
                    item
                    for item in phones
                    if item["name"].strip().casefold() == model.casefold()
                ),
                None,
            )

            if phone is None:
                return _get_response(
                    404,
                    {"detail": (f"Phone model '{model}' was not found for '{brand}'.")},
                )

            specifications = service.get_phone_specifications(phone["url"])

            return _get_response(
                200,
                {
                    "brand": brand,
                    "model": phone["name"],
                    "specifications": specifications,
                },
            )

        return _get_response(404, {"detail": "Endpoint not found."})

    except ManufacturerNotFoundError as error:
        return _get_response(404, {"detail": str(error)})

    except requests.RequestException:
        logger.exception("GSMArena request failed.")

        return _get_response(
            503,
            {"detail": "GSMArena is temporarily unavailable."},
        )

    except Exception:
        logger.exception("Unexpected Lambda error.")

        return _get_response(
            500,
            {"detail": "Internal server error."},
        )
