"""Turns a stock in a buy zone into an idea with a plan and plain-word reasons. Pure."""

from datetime import datetime

from steady.constants import (
    HARD_EXIT_PCT,
    IDEA_NEW,
    PAPER_CAPITAL,
    PER_STOCK_CAP_PCT,
)
from steady.core.plan import PlanInput, build_plan
from steady.core.zones import level_price
from steady.domain import Idea
from steady.services.stocks import StockView
from steady.utils.format import inr


def _latest_profit(view: StockView) -> str:
    profit = view.seed.financials[-1].net_profit if view.seed.financials else None
    return "not known" if profit is None else inr(profit)


def build_idea(
    view: StockView, approved_count: int, idea_id: str, created_at: datetime
) -> Idea | None:
    """An idea for the steps this stock has reached, or None when there are none."""
    plan = build_plan(
        PlanInput(
            reference_high=view.reference_high,
            last_price=view.last_price,
            below_pct=view.below_high_pct,
            capital=PAPER_CAPITAL,
            per_stock_cap_pct=PER_STOCK_CAP_PCT,
            approved_count=approved_count,
            lot_size=view.seed.lot_size,
        )
    )
    if not any(step.reached and not step.filled for step in plan.steps):
        return None
    business = view.seed.business
    return Idea(
        id=idea_id,
        symbol=view.seed.symbol,
        name=view.seed.name,
        zone=view.zone,
        plan=plan,
        target_price=view.reference_high,
        hard_exit_price=level_price(view.reference_high, HARD_EXIT_PCT),
        evidence_score=view.evidence,
        reasons=(
            f"{view.below_high_pct}% below its 6-month high of {inr(view.reference_high)}.",
            f"Back within a year after {view.recovered12m_pct:.0f}% of its {view.falls10} "
            "past 10% falls.",
            f"Latest year net profit {_latest_profit(view)} crore; "
            f"business rated {business.durability.lower()}.",
        ),
        risks=(business.watch, f"Its worst fall since 2016 was {abs(view.max_drawdown_pct):.0f}%."),
        status=IDEA_NEW,
        created_at=created_at,
    )


def filter_ideas(
    ideas: list[Idea],
    instrument_type: str | None = None,
    status: str | None = None,
    min_zone: int = 0,
    min_score: int = 0,
) -> list[Idea]:
    return [
        i
        for i in ideas
        if instrument_type in (None, i.plan.instrument_type)
        and status in (None, i.status)
        and i.zone >= min_zone
        and i.evidence_score >= min_score
    ]
