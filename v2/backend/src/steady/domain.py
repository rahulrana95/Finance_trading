"""Plain data shapes shared by adapters and services."""

from dataclasses import dataclass
from datetime import date

from steady.core.scoring import FinYear


@dataclass(frozen=True)
class Close:
    day: date
    close: float


@dataclass(frozen=True)
class Business:
    durability: str
    ai_impact: str
    watch: str
    revenue_label: str


@dataclass(frozen=True)
class StockSeed:
    symbol: str
    name: str
    industry: str
    status: str
    lot_size: int | None
    is_lender: bool
    financials: tuple[FinYear, ...]
    debt_to_equity: float | None
    promoter_pledge_pct: float | None
    business: Business
