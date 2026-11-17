"""Interfaces the services depend on; adapters implement them."""

from typing import Protocol

from steady.domain import Close


class PriceSourceError(Exception):
    """The price source could not give usable prices for a symbol."""


class PriceSource(Protocol):
    name: str
    official: bool

    def daily_closes(self, symbol: str) -> list[Close]:
        """Daily closes, oldest first. Raises PriceSourceError."""
        ...
