import logging
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import requests

from company_lookup.database.connection import DATABASE_PATH
from company_lookup.database.repository import PhoneRepository
from company_lookup.exceptions import ManufacturerNotFoundError
from company_lookup.models.phone import Phone
from company_lookup.scraper.client import GSMArenaScraper

logger = logging.getLogger(__name__)


class ScraperProtocol(Protocol):
    """Define the scraper operations required by the lookup service."""

    def get_manufacturers(self) -> dict[str, str]:
        """Retrieve available manufacturers."""

    def get_all_phone_links(self, listing_url: str) -> list[dict[str, str]]:
        """Retrieve phones belonging to a manufacturer."""

    def get_phone_specifications(
        self,
        phone_url: str,
    ) -> dict[str, dict[str, list[str]]]:
        """Retrieve specifications for a phone."""


class PhoneLookupService:
    """Coordinate phone data retrieval between scraper and database."""

    def __init__(
        self,
        scraper: ScraperProtocol | None = None,
        repository: PhoneRepository | None = None,
        database_path: str | Path = DATABASE_PATH,
        cache_ttl_days: int = 7,
    ) -> None:
        """Initialize the service with dependencies and cache configuration."""
        if cache_ttl_days < 1:
            raise ValueError("cache_ttl_days must be at least 1")

        self.scraper = scraper if scraper is not None else GSMArenaScraper()
        self.repository = (
            repository if repository is not None else PhoneRepository(database_path)
        )
        self.cache_ttl = timedelta(days=cache_ttl_days)

    def _is_cache_fresh(self, fetched_at: str | None) -> bool:
        """Check whether a cached timestamp is within the configured TTL."""
        if fetched_at is None:
            return False

        cached_time = datetime.fromisoformat(fetched_at)

        if cached_time.tzinfo is None:
            cached_time = cached_time.replace(tzinfo=timezone.utc)

        current_time = datetime.now(timezone.utc)

        return current_time - cached_time < self.cache_ttl

    @staticmethod
    def _format_phones(phones: list[dict[str, str]]) -> list[dict[str, str]]:
        """Convert repository phone records into service response objects."""
        return [
            asdict(Phone(name=phone["name"], url=phone["detail_url"]))
            for phone in phones
        ]

    def get_manufacturers(self) -> dict[str, str]:
        """Retrieve fresh manufacturers or refresh the cached directory."""
        cached_manufacturers: dict[str, str] = {}
        fetched_at = None

        try:
            cached_manufacturers, fetched_at = self.repository.get_manufacturers_cache()

            if cached_manufacturers and self._is_cache_fresh(fetched_at):
                return cached_manufacturers

        except sqlite3.Error:
            logger.exception("Failed to retrieve manufacturers from database.")

        try:
            manufacturers = self.scraper.get_manufacturers()
        except requests.exceptions.RequestException:
            if cached_manufacturers:
                logger.warning(
                    "Manufacturer refresh failed. Returning stale cached data.",
                    exc_info=True,
                )
                return cached_manufacturers
            raise

        try:
            self.repository.save_manufacturers(manufacturers)
        except sqlite3.Error:
            logger.exception("Failed to save manufacturers to database.")

        return manufacturers

    def get_phones(self, manufacturer_name: str) -> list[dict[str, str]]:
        """Retrieve manufacturer phones using a case-insensitive name."""
        manufacturers = self.get_manufacturers()

        requested_name = manufacturer_name.strip().casefold()

        canonical_name = next(
            (name for name in manufacturers if name.casefold() == requested_name),
            None,
        )

        if canonical_name is None:
            raise ManufacturerNotFoundError(
                f"Manufacturer '{manufacturer_name}' was not found."
            )

        cached_phones: list[dict[str, str]] = []
        fetched_at = None

        try:
            cached_phones, fetched_at = self.repository.get_phones_cache(canonical_name)

            if fetched_at is not None and self._is_cache_fresh(fetched_at):
                return self._format_phones(cached_phones)

        except sqlite3.Error:
            logger.exception("Failed to retrieve phones from database.")

        listing_url = manufacturers[canonical_name]

        try:
            scraped_phones = self.scraper.get_all_phone_links(listing_url)
        except requests.exceptions.RequestException:
            if fetched_at is not None:
                logger.warning(
                    "Phone refresh failed. Returning stale cached data.",
                    exc_info=True,
                )
                return self._format_phones(cached_phones)
            raise

        repository_phones = [
            {
                "name": phone["name"],
                "detail_url": phone["url"],
            }
            for phone in scraped_phones
        ]

        try:
            self.repository.save_phones({canonical_name: repository_phones})
        except sqlite3.Error:
            logger.exception("Failed to save phones to database.")

        return scraped_phones

    def get_phone_specifications(
        self,
        phone_url: str,
    ) -> dict[str, dict[str, list[str]]]:
        """Retrieve fresh specifications or refresh the cached data."""
        cached_specifications = None
        fetched_at = None

        try:
            cached_specifications, fetched_at = (
                self.repository.get_specifications_cache(phone_url)
            )

            if (
                fetched_at is not None
                and self._is_cache_fresh(fetched_at)
                and cached_specifications is not None
            ):
                return cached_specifications

        except sqlite3.Error:
            logger.exception("Failed to retrieve specifications from database.")

        try:
            specifications = self.scraper.get_phone_specifications(phone_url)
        except requests.exceptions.RequestException:
            if fetched_at is not None and cached_specifications is not None:
                logger.warning(
                    "Specification refresh failed. Returning stale cached data.",
                    exc_info=True,
                )
                return cached_specifications
            raise

        try:
            self.repository.save_specifications(phone_url, specifications)
        except sqlite3.Error:
            logger.exception("Failed to save specifications to database.")

        return specifications
