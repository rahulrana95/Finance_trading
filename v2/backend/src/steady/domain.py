"""Plain data shapes shared by adapters and services."""

from dataclasses import dataclass, field
from datetime import date, datetime

from steady.core.plan import Plan
from steady.core.scoring import FinYear
from steady.core.screen import Odds


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


@dataclass(frozen=True)
class RunStep:
    seq: int
    at: datetime
    subject: str
    level: str
    message: str


@dataclass
class Run:
    id: str
    kind: str
    status: str
    started_at: datetime
    summary: str
    finished_at: datetime | None = None
    steps: list[RunStep] = field(default_factory=list)


@dataclass(frozen=True)
class Idea:
    id: str
    symbol: str
    name: str
    zone: int
    plan: Plan
    target_price: float
    hard_exit_price: float
    evidence_score: int
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    status: str
    created_at: datetime


@dataclass(frozen=True)
class Listing:
    symbol: str
    name: str
    industry: str


@dataclass(frozen=True)
class Evidence:
    """One thing the confidence rests on, and whether it holds today."""

    label: str
    met: bool
    detail: str


@dataclass(frozen=True)
class ScreenRow:
    """One stock that is in a deep fall today."""

    symbol: str
    name: str
    industry: str
    last_price: float
    price_as_of: str
    year_high: float
    below_pct: float
    level: float
    own_falls: int
    own_higher_after_year: int
    own_falls_with_year: int
    worst_day_pct: float  # biggest one-day drop in the last year; a huge one suggests a demerger
    confidence: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Screen:
    id: str
    created_at: datetime
    universe: int
    priced: int
    market_below_pct: float
    market: str
    odds: tuple[Odds, ...]
    rows: tuple[ScreenRow, ...]
