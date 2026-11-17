"""Turning a stock in a buy zone into an idea, and filtering ideas."""

from dataclasses import replace
from datetime import UTC, date, datetime

from steady.adapters.seed import load_seed_stocks
from steady.constants import IDEA_EXPIRED, IDEA_NEW
from steady.domain import Close, StockSeed
from steady.services.ideas import build_idea, filter_ideas
from steady.services.stocks import StockView, build_view
from tests.support import FakePrices, closes

TODAY = date(2026, 11, 17)
NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
SEEDS = load_seed_stocks()
ICICI, NESTLE = SEEDS[0], SEEDS[1]
SLIDE = closes([100.0] * 60 + [95.0, 90.0, 85.0])
FLAT = closes([100.0] * 63)
DEEP = closes([400.0] * 60 + [350.0, 300.0, 260.0])  # 35% below: all three steps reached


def view(seed: StockSeed = NESTLE, prices: list[Close] = SLIDE) -> StockView:
    return build_view(seed, prices, FakePrices(), TODAY)


def test_an_idea_carries_plan_target_exit_and_reasons():
    idea = build_idea(view(), approved_count=5, idea_id="i1", created_at=NOW)
    assert idea is not None
    assert (idea.id, idea.symbol, idea.name, idea.zone) == ("i1", "NESTLEIND", "Nestle India", 1)
    assert (idea.status, idea.created_at) == (IDEA_NEW, NOW)
    assert (idea.target_price, idea.hard_exit_price) == (100.0, 60.0)
    assert idea.plan.allocation == 400_000
    assert [s.amount for s in idea.plan.steps] == [66_666, 133_333, 200_000]
    assert idea.plan.instrument_type == "cash"
    assert idea.reasons[0] == "15.0% below its 6-month high of 100."
    assert idea.reasons[1] == "Back within a year after 0% of its 1 past 10% falls."
    assert idea.reasons[2] == "Latest year net profit 3,499 crore; business rated strong."
    assert idea.risks[0] == NESTLE.business.watch
    assert idea.risks[1] == "Its worst fall since 2016 was 15%."


def test_a_deep_fall_with_a_lot_that_fits_is_a_combo():
    idea = build_idea(view(ICICI, DEEP), approved_count=5, idea_id="i1", created_at=NOW)
    assert idea is not None
    assert idea.zone == 3
    assert idea.plan.instrument_type == "combo"
    assert idea.plan.steps[2].quantity == 700


def test_no_idea_outside_the_buy_zones():
    assert build_idea(view(prices=FLAT), 5, "i1", NOW) is None


def test_missing_profit_is_said_plainly():
    no_numbers = replace(NESTLE, financials=type(NESTLE.financials)())
    idea = build_idea(view(no_numbers), 5, "i1", NOW)
    assert idea is not None
    assert "net profit not known" in idea.reasons[2]


def test_filters_narrow_the_list():
    cash = build_idea(view(), 5, "cash", NOW)
    combo = build_idea(view(ICICI, DEEP), 5, "combo", NOW)
    assert cash is not None
    assert combo is not None
    old = replace(cash, id="old", status=IDEA_EXPIRED)
    ideas = [cash, combo, old]
    assert filter_ideas(ideas) == ideas
    assert filter_ideas(ideas, instrument_type="combo") == [combo]
    assert filter_ideas(ideas, status=IDEA_EXPIRED) == [old]
    assert filter_ideas(ideas, min_zone=2) == [combo]
    assert filter_ideas(ideas, min_score=101) == []
