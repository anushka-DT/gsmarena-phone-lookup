import json
import logging
from io import StringIO
from uuid import UUID

from fastapi.testclient import TestClient

from company_lookup.api.main import app
from company_lookup.logging_config import JSONFormatter


def capture_request_logs(client, headers=None):
    """Capture JSON-formatted application logs generated during an API request."""
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    original_level = root_logger.level

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    try:
        response = client.get("/health", headers=headers)
        log_output.seek(0)

        log_records = [
            record
            for line in log_output.getvalue().splitlines()
            if (record := json.loads(line))["logger"] == "company_lookup.api.main"
        ]
    finally:
        root_logger.removeHandler(handler)
        root_logger.setLevel(original_level)
        handler.close()

    return response, log_records


def test_health_check_returns_healthy_status():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_has_correct_metadata():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200

    api_schema = response.json()

    assert api_schema["info"]["title"] == "Phone Lookup API"
    assert api_schema["info"]["version"] == "1.0.0"


def test_request_generates_unique_request_id():
    client = TestClient(app)

    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]

    assert response.status_code == 200
    assert UUID(request_id)


def test_request_preserves_provided_request_id():
    client = TestClient(app)
    request_id = "test-request-123"

    response = client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_request_logs_contain_generated_request_id():
    client = TestClient(app)

    response, log_records = capture_request_logs(client)

    request_id = response.headers["X-Request-ID"]

    assert response.status_code == 200
    assert len(log_records) == 2

    assert all(record["request_id"] == request_id for record in log_records)

    assert log_records[0]["message"] == "Incoming request: GET /health"
    assert log_records[1]["message"] == "Request completed with status 200"

    assert all(record["level"] == "INFO" for record in log_records)


def test_request_logs_contain_provided_request_id():
    client = TestClient(app)
    request_id = "integration-test-request-123"

    response, log_records = capture_request_logs(
        client,
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert len(log_records) == 2

    assert all(record["request_id"] == request_id for record in log_records)
