"""Define the phone data model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Manufacturer:
    """Represent a phone manufacturer."""

    name: str
    listing_url: str


@dataclass(frozen=True)
class Phone:
    """Represent a mobile phone."""

    name: str
    url: str
