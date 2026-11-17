"""Response shapes for the API."""

from datetime import datetime

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
