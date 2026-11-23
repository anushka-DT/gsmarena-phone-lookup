from unittest.mock import Mock, patch

import pytest
import requests

from company_lookup import GSMArenaScraper


def make_response(html: str) -> Mock:
    """Create a successful mock HTTP response."""
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None
    return response


@pytest.fixture(autouse=True)
def disable_request_delay(monkeypatch):
    """Disable real request delays during ordinary tests."""
    monkeypatch.setattr(GSMArenaScraper, "REQUEST_DELAY", 0)


@patch("company_lookup.scraper.client.requests.get")
def test_get_phone_links(mock_get):
    html = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="samsung_galaxy_s24_ultra-12771.php">
                        <img title="Samsung Galaxy S24 Ultra Android smartphone.">
                        <strong><span>Galaxy S24 Ultra</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    mock_get.return_value = make_response(html)

    scraper = GSMArenaScraper()
    listing_url = "https://www.gsmarena.com/samsung-phones-9.php"

    result = scraper.get_phone_links(listing_url)

    assert result == [
        {
            "name": "Galaxy S24 Ultra",
            "url": "https://www.gsmarena.com/samsung_galaxy_s24_ultra-12771.php",
        }
    ]

    mock_get.assert_called_once_with(
        listing_url,
        headers=GSMArenaScraper.HEADERS,
        timeout=GSMArenaScraper.REQUEST_TIMEOUT,
    )


@patch("company_lookup.scraper.client.requests.get")
def test_get_phone_links_raises_http_error(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_get.return_value = mock_response

    scraper = GSMArenaScraper()

    with pytest.raises(requests.exceptions.HTTPError):
        scraper.get_phone_links("https://www.gsmarena.com/samsung-phones-9.php")


@patch("company_lookup.scraper.client.requests.get")
def test_get_manufacturers(mock_get):
    html = """
    <table>
        <tr>
            <td>
                <a href="samsung-phones-9.php">
                    Samsung<span>100 devices</span>
                </a>
            </td>
            <td>
                <a href="apple-phones-48.php">
                    Apple<span>50 devices</span>
                </a>
            </td>
            <td>
                <a href="xiaomi-phones-80.php">
                    Xiaomi<span>40 devices</span>
                </a>
            </td>
        </tr>
    </table>
    """

    mock_get.return_value = make_response(html)

    scraper = GSMArenaScraper()
    result = scraper.get_manufacturers()

    assert result == {
        "Samsung": "https://www.gsmarena.com/samsung-phones-9.php",
        "Apple": "https://www.gsmarena.com/apple-phones-48.php",
        "Xiaomi": "https://www.gsmarena.com/xiaomi-phones-80.php",
    }

    mock_get.assert_called_once_with(
        GSMArenaScraper.MANUFACTURERS_URL,
        headers=GSMArenaScraper.HEADERS,
        timeout=GSMArenaScraper.REQUEST_TIMEOUT,
    )


@patch("company_lookup.scraper.client.requests.get")
def test_get_manufacturers_removes_duplicates(mock_get):
    html = """
    <table>
        <tr>
            <td>
                <a href="samsung-phones-9.php">Samsung</a>
            </td>
            <td>
                <a href="samsung-phones-9.php">SAMSUNG</a>
            </td>
        </tr>
    </table>
    """

    mock_get.return_value = make_response(html)

    scraper = GSMArenaScraper()
    result = scraper.get_manufacturers()

    assert len(result) == 1
    assert result["Samsung"] == "https://www.gsmarena.com/samsung-phones-9.php"


@patch("company_lookup.scraper.client.requests.get")
def test_get_manufacturers_ignores_invalid_links(mock_get):
    html = """
    <table>
        <tr>
            <td>
                <a href="samsung-phones-9.php">Samsung</a>
            </td>
            <td>
                <a href="">Invalid URL</a>
            </td>
            <td>
                <a href="apple-phones-48.php"></a>
            </td>
            <td>
                <a>Missing URL</a>
            </td>
        </tr>
    </table>
    """

    mock_get.return_value = make_response(html)

    scraper = GSMArenaScraper()
    result = scraper.get_manufacturers()

    assert result == {"Samsung": "https://www.gsmarena.com/samsung-phones-9.php"}


@patch("company_lookup.scraper.client.requests.get")
def test_get_manufacturers_raises_http_error(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_get.return_value = mock_response

    scraper = GSMArenaScraper()

    with pytest.raises(requests.exceptions.HTTPError):
        scraper.get_manufacturers()


@patch("company_lookup.scraper.client.requests.get")
def test_get_all_phone_links_fetches_multiple_pages(mock_get):
    first_page = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="phone_one.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone One</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <a href="samsung-page-2.php"
       class="prevnextbutton"
       title="Next page">►</a>
    """

    second_page = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="phone_two.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone Two</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    mock_get.side_effect = [
        make_response(first_page),
        make_response(second_page),
    ]

    scraper = GSMArenaScraper()
    listing_url = "https://www.gsmarena.com/samsung-phones-9.php"

    result = scraper.get_all_phone_links(listing_url)

    assert result == [
        {
            "name": "Phone One",
            "url": "https://www.gsmarena.com/phone_one.php",
        },
        {
            "name": "Phone Two",
            "url": "https://www.gsmarena.com/phone_two.php",
        },
    ]

    assert mock_get.call_count == 2


@patch("company_lookup.scraper.client.requests.get")
def test_get_all_phone_links_removes_duplicate_phone_urls(mock_get):
    first_page = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="phone_one.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone One</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <a href="samsung-page-2.php"
       class="prevnextbutton"
       title="Next page">►</a>
    """

    second_page = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="phone_one.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone One Duplicate</span></strong>
                    </a>
                </li>
                <li>
                    <a href="phone_two.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone Two</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    mock_get.side_effect = [
        make_response(first_page),
        make_response(second_page),
    ]

    scraper = GSMArenaScraper()
    result = scraper.get_all_phone_links(
        "https://www.gsmarena.com/samsung-phones-9.php"
    )

    assert len(result) == 2
    assert result[0]["name"] == "Phone One"
    assert result[1]["name"] == "Phone Two"


@patch("company_lookup.scraper.client.requests.get")
def test_get_all_phone_links_prevents_pagination_loop(mock_get):
    first_page_url = "https://www.gsmarena.com/samsung-phones-9.php"
    second_page_url = "https://www.gsmarena.com/samsung-page-2.php"

    first_page = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="phone_one.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone One</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <a href="samsung-page-2.php"
       class="prevnextbutton"
       title="Next page">►</a>
    """

    second_page = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="phone_two.php">
                        <img title="Android smartphone.">
                        <strong><span>Phone Two</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <a href="samsung-phones-9.php"
       class="prevnextbutton"
       title="Next page">►</a>
    """

    mock_get.side_effect = [
        make_response(first_page),
        make_response(second_page),
    ]

    scraper = GSMArenaScraper()
    result = scraper.get_all_phone_links(first_page_url)

    assert len(result) == 2
    assert mock_get.call_count == 2

    requested_urls = [call.args[0] for call in mock_get.call_args_list]

    assert requested_urls == [first_page_url, second_page_url]


@patch("company_lookup.scraper.client.requests.get")
def test_get_phone_specifications(mock_get):
    html = """
    <table id="specs-list">
        <tr>
            <th>Network</th>
        </tr>
        <tr>
            <td class="ttl">Technology</td>
            <td class="nfo">GSM / HSPA / LTE / 5G</td>
        </tr>
        <tr>
            <th>Launch</th>
        </tr>
        <tr>
            <td class="ttl">Announced</td>
            <td class="nfo">2024, January 17</td>
        </tr>
    </table>
    """

    mock_get.return_value = make_response(html)

    scraper = GSMArenaScraper()
    phone_url = "https://www.gsmarena.com/samsung_galaxy_s24_ultra-12771.php"

    result = scraper.get_phone_specifications(phone_url)

    assert result == {
        "Network": {
            "Technology": ["GSM / HSPA / LTE / 5G"],
        },
        "Launch": {
            "Announced": ["2024, January 17"],
        },
    }

    mock_get.assert_called_once_with(
        phone_url,
        headers=GSMArenaScraper.HEADERS,
        timeout=GSMArenaScraper.REQUEST_TIMEOUT,
    )


@patch("company_lookup.scraper.client.requests.get")
def test_get_phone_specifications_raises_http_error(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_get.return_value = mock_response

    scraper = GSMArenaScraper()
    phone_url = "https://www.gsmarena.com/samsung_galaxy_s24_ultra-12771.php"

    with pytest.raises(requests.exceptions.HTTPError):
        scraper.get_phone_specifications(phone_url)


@patch("company_lookup.scraper.retry.time.sleep")
@patch("company_lookup.scraper.client.requests.get")
def test_get_phone_links_retries_after_server_error(mock_get, mock_sleep):
    server_error = requests.exceptions.HTTPError(response=Mock(status_code=503))

    successful_response = make_response("""
        <div id="review-body">
            <div class="makers">
                <ul>
                    <li>
                        <a href="phone_one.php">
                            <img title="Android smartphone.">
                            <strong><span>Phone One</span></strong>
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    """)

    mock_get.side_effect = [
        server_error,
        successful_response,
    ]

    scraper = GSMArenaScraper()

    result = scraper.get_phone_links("https://www.gsmarena.com/samsung-phones-9.php")

    assert result == [
        {
            "name": "Phone One",
            "url": "https://www.gsmarena.com/phone_one.php",
        }
    ]

    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1

    actual_delay = mock_sleep.call_args.args[0]
    assert 0.5 <= actual_delay <= 1.5


@patch("company_lookup.scraper.client.time.monotonic")
@patch("company_lookup.scraper.client.time.sleep")
@patch("company_lookup.scraper.client.requests.get")
def test_requests_respect_minimum_interval(
    mock_get,
    mock_sleep,
    mock_monotonic,
    monkeypatch,
):
    monkeypatch.setattr(GSMArenaScraper, "REQUEST_DELAY", 1.0)

    mock_get.side_effect = [
        make_response("<html>First page</html>"),
        make_response("<html>Second page</html>"),
    ]

    mock_monotonic.side_effect = [
        100.0,
        100.2,
        101.0,
    ]

    scraper = GSMArenaScraper()

    scraper._get_page_html("https://example.com/page1")
    scraper._get_page_html("https://example.com/page2")

    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()
    assert mock_sleep.call_args.args[0] == pytest.approx(0.8)
