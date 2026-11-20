"""Response shapes for the API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Health(BaseModel):
    status: str
    service: str
    version: str
    time: datetime


class CamelModel(BaseModel):
    """Sends camelCase field names, which is what the interface expects."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FinYearOut(CamelModel):
    period: str
    revenue: float | None
    net_profit: float | None


class BusinessOut(CamelModel):
    durability: str
    ai_impact: str
    watch: str
    revenue_label: str


class ScoresOut(CamelModel):
    stability: int
    financial: int
    data_quality: int
    evidence: int


class StockOut(CamelModel):
    symbol: str
    name: str
    industry: str
    status: str
    last_price: float
    price_as_of: str
    price_source: str
    reference_high: float
    below_high_pct: float
    zone: int
    lot_size: int | None
    is_lender: bool
    falls10: int
    recovered12m_pct: float = Field(alias="recovered12mPct")
    longest_recovery_days: int
    max_drawdown_pct: float
    history_years: float
    financials: list[FinYearOut]
    debt_to_equity: float | None
    promoter_pledge_pct: float | None
    business: BusinessOut
    scores: ScoresOut
    needs: list[str]
    history: list[float]


class RunStepOut(CamelModel):
    seq: int
    at: datetime
    subject: str
    level: str
    message: str


class RunOut(CamelModel):
    id: str
    kind: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    summary: str
    steps: list[RunStepOut]


class RunRequest(BaseModel):
    kind: Literal["on_demand", "dry_run"] = "on_demand"


class PlanStepOut(CamelModel):
    step: int
    level_pct: float
    level_price: float
    amount: int
    instrument: str
    quantity: int
    reached: bool
    filled: bool


class IdeaOut(CamelModel):
    id: str
    symbol: str
    name: str
    zone: int
    instrument_type: str
    steps: list[PlanStepOut]
    target_price: float
    hard_exit_price: float
    evidence_score: int
    reasons: list[str]
    risks: list[str]
    futures_note: str
    status: str
    created_at: datetime


class OddsOut(CamelModel):
    level: float
    market_down: bool
    events: int
    gain10_6m_pct: float = Field(alias="gain10In6mPct")
    gain20_6m_pct: float = Field(alias="gain20In6mPct")
    higher_6m_pct: float = Field(alias="higherAfter6mPct")
    events_12m: int = Field(alias="eventsWithYear")
    gain30_12m_pct: float = Field(alias="gain30In12mPct")
    higher_12m_pct: float = Field(alias="higherAfter12mPct")
    fell_further_12m_pct: float = Field(alias="fellFurtherPct")


class ScreenRowOut(CamelModel):
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
    worst_day_pct: float


class ScreenOut(CamelModel):
    id: str
    created_at: datetime
    universe: int
    priced: int
    market_below_pct: float
    market_down: bool
    odds: list[OddsOut]
    rows: list[ScreenRowOut]


class ScreenStateOut(CamelModel):
    running: bool
    error: str | None
    screen: ScreenOut | None
