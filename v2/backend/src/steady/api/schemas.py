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
