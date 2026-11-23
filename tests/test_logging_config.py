import json
import logging
import sys

from company_lookup.logging_config import (
    JSONFormatter,
    configure_logging,
    request_id_context,
)


def create_log_record(
    message: str = "Test log message",
) -> logging.LogRecord:
    """Create a log record for formatter tests."""
    return logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_json_formatter_includes_required_fields():
    formatter = JSONFormatter()
    record = create_log_record()

    result = json.loads(formatter.format(record))

    assert result["level"] == "INFO"
    assert result["logger"] == "test_logger"
    assert result["message"] == "Test log message"
    assert "timestamp" in result
    assert result["request_id"] == "-"


def test_json_formatter_includes_request_id():
    formatter = JSONFormatter()
    record = create_log_record()
    token = request_id_context.set("request-123")

    try:
        result = json.loads(formatter.format(record))
    finally:
        request_id_context.reset(token)

    assert result["request_id"] == "request-123"


def test_json_formatter_includes_exception_details():
    formatter = JSONFormatter()
    record = create_log_record("An error occurred")

    try:
        raise ValueError("Invalid test value")
    except ValueError:
        record.exc_info = sys.exc_info()

    result = json.loads(formatter.format(record))

    assert "exception" in result
    assert "ValueError: Invalid test value" in result["exception"]


def test_configure_logging_sets_json_formatter(monkeypatch):
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()

    monkeypatch.setattr(root_logger, "handlers", [handler])
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: None)

    configure_logging()

    assert isinstance(handler.formatter, JSONFormatter)
