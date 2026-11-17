"""The stepped plan and the shares / futures choice (TEST_PLAN P01-P12)."""

from dataclasses import replace

from steady.core.plan import PlanInput, build_plan

BASE = PlanInput(
    reference_high=1000.0, last_price=880.0, below_pct=12.0, capital=2_000_000,
    per_stock_cap_pct=20.0, approved_count=5, lot_size=None,
)  # fmt: skip


def offered(below: float, filled: frozenset[int] = frozenset()) -> list[int]:
    plan = build_plan(replace(BASE, below_pct=below, filled_steps=filled))
    return [s.step for s in plan.steps if s.reached and not s.filled]


def test_allocation_is_the_smaller_of_the_cap_and_an_equal_share():  # P01
    assert build_plan(BASE).allocation == 400_000
    assert build_plan(replace(BASE, approved_count=10)).allocation == 200_000
    assert build_plan(replace(BASE, approved_count=0)).allocation == 400_000


def test_steps_split_the_allocation_one_two_three():  # P02
    assert [s.amount for s in build_plan(BASE).steps] == [66_666, 133_333, 200_000]


def test_levels_are_priced_from_the_reference_high():
    assert [(s.level_pct, s.level_price) for s in build_plan(BASE).steps] == [
        (10.0, 900.0), (20.0, 800.0), (30.0, 700.0),
    ]  # fmt: skip


def test_only_reached_and_unfilled_steps_are_offered():  # P03-P06
    assert offered(12.0) == [1]
    assert offered(22.0) == [1, 2]
    assert offered(22.0, frozenset({1})) == [2]
    assert offered(35.0, frozenset({1, 2, 3})) == []
    assert offered(5.0) == []


def test_shares_are_whole_and_within_the_step_amount():  # P07
    step = build_plan(BASE).steps[0]
    assert (step.instrument, step.quantity) == ("cash", 75)
    assert step.quantity * BASE.last_price <= step.amount


def test_a_step_smaller_than_one_share_has_zero_quantity():  # P08
    assert build_plan(replace(BASE, capital=10_000)).steps[0].quantity == 0


def test_step_three_uses_a_futures_lot_when_one_fits():  # P09
    plan = build_plan(replace(BASE, below_pct=35.0, last_price=650.0, lot_size=300))
    assert [s.instrument for s in plan.steps] == ["cash", "cash", "future"]
    assert plan.steps[2].quantity == 300
    assert plan.instrument_type == "combo"
    assert plan.futures_note == "Step 3 uses one futures lot."


def test_a_lot_larger_than_the_step_falls_back_to_shares():  # P10
    plan = build_plan(replace(BASE, below_pct=35.0, last_price=650.0, lot_size=700))
    assert plan.instrument_type == "cash"
    assert plan.futures_note == (
        "Futures not offered: one lot is worth about 4,55,000, "
        "more than the 2,00,000 for this step."
    )


def test_an_unknown_lot_size_is_reported():  # P11
    assert build_plan(BASE).futures_note == "Futures not offered: lot size needs data."


def test_all_futures_when_allowed_from_step_one_and_every_lot_fits():  # P12
    plan = build_plan(
        replace(BASE, futures_from_step=1, last_price=100.0, lot_size=100, below_pct=35.0)
    )
    assert plan.instrument_type == "future"


def test_futures_can_be_switched_off_entirely():
    plan = build_plan(replace(BASE, futures_from_step=4, lot_size=1))
    assert plan.futures_note == "Futures are only considered from step 4."
    assert plan.instrument_type == "cash"


def test_nothing_offered_is_a_cash_plan():
    assert build_plan(replace(BASE, below_pct=0.0)).instrument_type == "cash"
