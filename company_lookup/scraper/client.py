import time
from typing import ClassVar
from urllib.parse import urljoin

import requests

from .parser import (
    get_next_page_url,
    parse_manufacturers,
    parse_phone_links,
    parse_specifications,
)
from .retry import INITIAL_DELAY, MAX_ATTEMPTS, retry


class GSMArenaScraper:
    """Fetch and parse phone information from GSMArena."""

    BASE_URL = "https://www.gsmarena.com/"
    MANUFACTURERS_URL = urljoin(BASE_URL, "makers.php3")

    REQUEST_TIMEOUT = 15
    REQUEST_DELAY = 1.0

    HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": "Mozilla/5.0",
    }

    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        initial_delay: float = INITIAL_DELAY,
    ) -> None:
        """Initialize the scraper with configurable retry settings."""
        self._last_request_time: float | None = None

        self._request_page = retry(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
        )(self._fetch_page_html)

    def _wait_for_request_interval(self) -> None:
        """Maintain the minimum interval between HTTP requests."""
        current_time = time.monotonic()

        if self._last_request_time is not None:
            elapsed = current_time - self._last_request_time
            remaining = self.REQUEST_DELAY - elapsed

            if remaining > 0:
                time.sleep(remaining)
                current_time = time.monotonic()

        self._last_request_time = current_time

    def _fetch_page_html(self, page_url: str) -> str:
        """Fetch HTML from a URL using the configured request timeout."""
        response = requests.get(
            page_url,
            headers=self.HEADERS,
            timeout=self.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text

    def _get_page_html(self, page_url: str) -> str:
        """Fetch a page with request pacing and retry handling."""
        self._wait_for_request_interval()
        return self._request_page(page_url)

    def get_manufacturers(self) -> dict[str, str]:
        """Retrieve available manufacturers."""
        html = self._get_page_html(self.MANUFACTURERS_URL)
        return parse_manufacturers(html, self.BASE_URL)

    def get_phone_links(self, listing_url: str) -> list[dict[str, str]]:
        """Retrieve phone links from a manufacturer's listing page."""
        html = self._get_page_html(listing_url)
        return self.parse_phone_links(html)

    def get_all_phone_links(self, listing_url: str) -> list[dict[str, str]]:
        """Retrieve phone links across all listing pages without duplicates."""
        all_phones = []
        seen_phone_urls = set()
        visited_page_urls = set()
        current_url = listing_url

        while current_url and current_url not in visited_page_urls:
            visited_page_urls.add(current_url)

            html = self._get_page_html(current_url)
            phones = self.parse_phone_links(html)

            for phone in phones:
                phone_url = phone["url"]

                if phone_url not in seen_phone_urls:
                    all_phones.append(phone)
                    seen_phone_urls.add(phone_url)

            current_url = self.get_next_page_url(html, current_url)

        return all_phones

    def get_phone_specifications(
        self,
        phone_url: str,
    ) -> dict[str, dict[str, list[str]]]:
        """Retrieve specifications for a phone."""
        html = self._get_page_html(phone_url)
        return self.parse_specifications(html)

    @classmethod
    def parse_phone_links(cls, html: str) -> list[dict[str, str]]:
        """Parse phone links from listing page HTML."""
        return parse_phone_links(html, cls.BASE_URL)

    @staticmethod
    def parse_specifications(
        html: str,
    ) -> dict[str, dict[str, list[str]]]:
        """Parse phone specifications from HTML."""
        return parse_specifications(html)

    @staticmethod
    def get_next_page_url(html: str, current_url: str) -> str | None:
        """Find the next listing page URL."""
        return get_next_page_url(html, current_url)
