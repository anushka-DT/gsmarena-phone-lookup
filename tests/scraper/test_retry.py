from unittest.mock import Mock, call, patch

import pytest
import requests

from company_lookup.scraper.retry import retry


@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_returns_result_on_first_attempt(mock_sleep):
    operation = Mock(return_value="success")

    result = retry()(operation)()

    assert result == "success"
    operation.assert_called_once()
    mock_sleep.assert_not_called()


@patch("company_lookup.scraper.retry.random.uniform", return_value=1)
@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_succeeds_after_connection_error(mock_sleep, mock_uniform):
    operation = Mock(
        side_effect=[
            requests.exceptions.ConnectionError("Connection failed"),
            "success",
        ]
    )

    result = retry()(operation)()

    assert result == "success"
    assert operation.call_count == 2
    mock_uniform.assert_called_once_with(0.5, 1.5)
    mock_sleep.assert_called_once_with(1)


@patch("company_lookup.scraper.retry.random.uniform", return_value=1)
@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_succeeds_after_timeout(mock_sleep, mock_uniform):
    operation = Mock(
        side_effect=[
            requests.exceptions.Timeout("Request timed out"),
            "success",
        ]
    )

    result = retry()(operation)()

    assert result == "success"
    assert operation.call_count == 2
    mock_uniform.assert_called_once_with(0.5, 1.5)
    mock_sleep.assert_called_once_with(1)


@patch("company_lookup.scraper.retry.random.uniform", return_value=1)
@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_succeeds_after_server_error(mock_sleep, mock_uniform):
    server_error = requests.exceptions.HTTPError(response=Mock(status_code=503))

    operation = Mock(
        side_effect=[
            server_error,
            "success",
        ]
    )

    result = retry()(operation)()

    assert result == "success"
    assert operation.call_count == 2
    mock_uniform.assert_called_once_with(0.5, 1.5)
    mock_sleep.assert_called_once_with(1)


@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_does_not_retry_client_error(mock_sleep):
    client_error = requests.exceptions.HTTPError(response=Mock(status_code=404))
    operation = Mock(side_effect=client_error)

    with pytest.raises(requests.exceptions.HTTPError):
        retry()(operation)()

    operation.assert_called_once()
    mock_sleep.assert_not_called()


@patch(
    "company_lookup.scraper.retry.random.uniform",
    side_effect=[1, 2],
)
@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_uses_exponential_backoff(mock_sleep, mock_uniform):
    operation = Mock(
        side_effect=[
            requests.exceptions.ConnectionError("First failure"),
            requests.exceptions.Timeout("Second failure"),
            "success",
        ]
    )

    result = retry()(operation)()

    assert result == "success"
    assert operation.call_count == 3
    assert mock_uniform.call_args_list == [
        call(0.5, 1.5),
        call(1.0, 3.0),
    ]
    assert mock_sleep.call_args_list == [
        call(1),
        call(2),
    ]


@patch(
    "company_lookup.scraper.retry.random.uniform",
    side_effect=[1, 2],
)
@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_raises_exception_after_maximum_attempts(
    mock_sleep,
    mock_uniform,
):
    operation = Mock(
        side_effect=requests.exceptions.ConnectionError("Connection failed")
    )

    with pytest.raises(requests.exceptions.ConnectionError):
        retry()(operation)()

    assert operation.call_count == 3
    assert mock_uniform.call_count == 2
    assert mock_sleep.call_args_list == [
        call(1),
        call(2),
    ]


@patch("company_lookup.scraper.retry.random.uniform", return_value=0.5)
@patch("company_lookup.scraper.retry.time.sleep")
def test_retry_applies_random_jitter(mock_sleep, mock_uniform):
    operation = Mock(
        side_effect=[
            requests.exceptions.ConnectionError("Connection failed"),
            "success",
        ]
    )

    result = retry()(operation)()

    assert result == "success"
    mock_uniform.assert_called_once_with(0.5, 1.5)
    mock_sleep.assert_called_once_with(0.5)


def test_retry_rejects_invalid_max_attempts():
    with pytest.raises(ValueError):
        retry(max_attempts=0)


def test_retry_rejects_negative_initial_delay():
    with pytest.raises(ValueError):
        retry(initial_delay=-1)
