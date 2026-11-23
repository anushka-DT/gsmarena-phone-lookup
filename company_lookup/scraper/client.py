from typing import ClassVar
from urllib.parse import urljoin

import requests

from .parser import (
    get_next_page_url,
    parse_manufacturers,
    parse_phone_links,
    parse_specifications,
)
from .retry import retry


class GSMArenaScraper:
    """Fetch and parse phone information from GSMArena."""

    BASE_URL = "https://www.gsmarena.com/"
    MANUFACTURERS_URL = urljoin(BASE_URL, "makers.php3")
    REQUEST_TIMEOUT = 15

    HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": "Mozilla/5.0",
    }

    def get_manufacturers(self) -> dict[str, str]:
        """Retrieve manufacturer names and their listing URLs."""
        html = self._get_page_html(self.MANUFACTURERS_URL)
        return parse_manufacturers(html, self.BASE_URL)

    @retry()
    def _get_page_html(self, page_url: str) -> str:
        """Fetch HTML content with retry for temporary request failures."""
        response = requests.get(
            page_url,
            headers=self.HEADERS,
            timeout=self.REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        return response.text

    def get_phone_links(self, listing_url: str) -> list[dict[str, str]]:
        """Fetch a manufacturer listing page and extract smartphone links."""
        html = self._get_page_html(listing_url)
        return self.parse_phone_links(html)

    def get_all_phone_links(self, listing_url: str) -> list[dict[str, str]]:
        """Fetch smartphone links from all pages of a manufacturer listing."""
        all_phones: list[dict[str, str]] = []
        seen_phone_urls: set[str] = set()
        visited_page_urls: set[str] = set()

        current_url: str | None = listing_url

        while current_url and current_url not in visited_page_urls:
            visited_page_urls.add(current_url)

            html = self._get_page_html(current_url)
            phones = self.parse_phone_links(html)

            for phone in phones:
                phone_url = phone["url"]

                if phone_url in seen_phone_urls:
                    continue

                all_phones.append(phone)
                seen_phone_urls.add(phone_url)

            current_url = self.get_next_page_url(html, current_url)

        return all_phones

    def get_phone_specifications(
        self,
        phone_url: str,
    ) -> dict[str, dict[str, list[str]]]:
        """Fetch and parse specifications for a phone."""
        html = self._get_page_html(phone_url)
        return self.parse_specifications(html)

    @classmethod
    def parse_phone_links(cls, html: str) -> list[dict[str, str]]:
        """Parse smartphone names and URLs from listing-page HTML."""
        return parse_phone_links(html, cls.BASE_URL)

    @staticmethod
    def parse_specifications(html: str) -> dict[str, dict[str, list[str]]]:
        """Parse phone specifications from detail-page HTML."""
        return parse_specifications(html)

    @staticmethod
    def get_next_page_url(html: str, current_url: str) -> str | None:
        """Find the next page in a manufacturer listing."""
        return get_next_page_url(html, current_url)
