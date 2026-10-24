from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fintrade.core.bars import DailyContractBar, OptionType
from fintrade.core.contract_specs import (
    MIN_OBSERVATIONS_FOR_INFERENCE,
    LotSizeSource,
    derive_expiry_specs,
    infer_lot_size,
)
from fintrade.core.errors import DataError
from tests.support.bars import make_bar, make_future

E1, E2 = date(2026, 10, 27), date(2026, 11, 3)
FRI = date(2026, 10, 23)


def _bar(day: date, oi: int, change: int, lot: int | None = None, **kw: object) -> DailyContractBar:
    return make_bar(trade_date=day, open_interest=oi, change_in_oi=change, lot_size=lot, **kw)


@pytest.mark.parametrize(
    ("values", "expected"),
    [([150, 225, -75], 75), ([0, 650, 1300], 650), ([0, 0], None), ([], None), ([-25], 25)],
)
def test_infer_lot_size(values: list[int], expected: int | None) -> None:
    assert infer_lot_size(values) == expected


@given(lot=st.integers(1, 2000), multiples=st.lists(st.integers(-500, 500), min_size=1))
def test_gcd_is_a_multiple_of_the_true_lot(lot: int, multiples: list[int]) -> None:
    result = infer_lot_size(m * lot for m in multiples)
    assert result is None or result % lot == 0


def _many(
    day: date, lot: int, count: int = MIN_OBSERVATIONS_FOR_INFERENCE
) -> list[DailyContractBar]:
    """`count` non-zero OI values that are all multiples of `lot`."""
    return [
        _bar(day, lot * (k + 2), lot, strike=Decimal(20000 + 50 * k)) for k in range(count // 2)
    ]


def test_inferred_from_old_format_bars() -> None:
    bars = [*_many(FRI, 75), *_many(date(2026, 10, 26), 75), make_future(lot_size=None)]
    (spec,) = derive_expiry_specs(bars)
    assert (spec.expiry, spec.lot_size, spec.source) == (E1, 75, LotSizeSource.INFERRED)
    assert (spec.first_traded, spec.last_traded) == (FRI, date(2026, 10, 26))
    assert (spec.observations, spec.oi_gcd, spec.oi_gcd_consistent) == (200, 75, True)


def test_too_few_observations_is_unknown() -> None:
    # Real case: 20 values gave a gcd of 150 when the lot was 75.
    (spec,) = derive_expiry_specs(_many(date(2026, 10, 26), 150, count=98))
    assert (spec.lot_size, spec.source, spec.oi_gcd) == (None, LotSizeSource.UNKNOWN, 150)


def test_data_ending_far_from_expiry_is_unknown() -> None:
    far_expiry = date(2026, 11, 9)  # 14 days after the last observation
    bars = _many(date(2026, 10, 26), 75)
    bars = [replace(b, expiry=far_expiry) for b in bars]
    (spec,) = derive_expiry_specs(bars)
    assert spec.source is LotSizeSource.UNKNOWN


def test_data_ending_13_days_before_expiry_is_trusted() -> None:
    bars = [replace(b, expiry=date(2026, 11, 8)) for b in _many(date(2026, 10, 26), 75)]
    (spec,) = derive_expiry_specs(bars)
    assert (spec.lot_size, spec.source) == (75, LotSizeSource.INFERRED)


def test_old_positions_outside_the_window_are_ignored() -> None:
    # Lot revised 75 -> 50: values from 20 days earlier would drag the gcd down to 25.
    bars = [_bar(date(2026, 10, 5), 75, 75), *_many(date(2026, 10, 26), 50)]
    (spec,) = derive_expiry_specs(bars)
    assert (spec.lot_size, spec.source, spec.observations) == (50, LotSizeSource.INFERRED, 100)


def test_window_includes_exactly_14_days() -> None:
    first, last = date(2026, 10, 13), date(2026, 10, 26)  # 14 days inclusive
    bars = [_bar(first, 75, 0), *_many(last, 150)]
    assert derive_expiry_specs(bars)[0].lot_size == 75
    bars = [_bar(first - timedelta(days=1), 75, 0), *_many(last, 150)]  # day 15: outside
    assert derive_expiry_specs(bars)[0].lot_size == 150


def test_stated_lot_sizes_used() -> None:
    bars = [
        _bar(FRI, 1300, 650, 65, expiry=E1),
        _bar(FRI, 650, 0, 65, expiry=E2, option_type=OptionType.PUT),
    ]
    specs = derive_expiry_specs(bars)
    assert [(s.expiry, s.lot_size, s.source, s.oi_gcd_consistent) for s in specs] == [
        (E1, 65, LotSizeSource.STATED, True),
        (E2, 65, LotSizeSource.STATED, True),
    ]


def test_revised_stated_lot_size_uses_the_latest_day() -> None:
    # Real case: long-dated contracts listed at lot 75, revised to 65.
    bars = [_bar(date(2026, 9, 1), 750, 75, 75), _bar(FRI, 650, 65, 65)]
    (spec,) = derive_expiry_specs(bars)
    assert (spec.lot_size, spec.source) == (65, LotSizeSource.STATED)


def test_stated_size_wins_and_mixed_open_interest_is_flagged() -> None:
    # Real case 2026-12-29: open interest mixes 75- and 65-unit positions, gcd 5.
    (spec,) = derive_expiry_specs([_bar(FRI, 75 + 65, 65, 65)])
    assert (spec.lot_size, spec.oi_gcd, spec.oi_gcd_consistent) == (65, 5, False)


def test_stated_lot_size_without_open_interest_is_fine() -> None:
    (spec,) = derive_expiry_specs([_bar(FRI, 0, 0, 65)])
    assert (spec.lot_size, spec.observations, spec.oi_gcd_consistent) == (65, 0, None)


def test_conflicting_stated_lot_sizes_on_one_day_is_an_error() -> None:
    bars = [_bar(FRI, 650, 0, 65), _bar(FRI, 750, 0, 75, option_type=OptionType.PUT)]
    with pytest.raises(DataError, match=r"conflicting stated lot sizes \[65, 75\] on 2026-10-23"):
        derive_expiry_specs(bars)


def test_newly_listed_expiry_without_open_interest_is_unknown() -> None:
    # Real case: weekly 2020-05-14 listed in March 2020 with zero open interest.
    (spec,) = derive_expiry_specs([_bar(FRI, 0, 0)])
    assert (spec.lot_size, spec.source, spec.observations) == (None, LotSizeSource.UNKNOWN, 0)
    assert spec.oi_gcd_consistent is None


def test_futures_only_gives_no_specs() -> None:
    assert derive_expiry_specs([make_future(), make_future(lot_size=None)]) == []
