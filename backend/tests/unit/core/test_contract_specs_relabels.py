"""Holiday-moved expiries that NSE re-labelled on live contracts (2023-06-29 -> 06-28)."""

from datetime import date

import pytest

from fintrade.core.contract_specs import ExpirySpec, LotSizeSource, expiry_relabels
from fintrade.core.errors import DataError

SRC = LotSizeSource.INFERRED


def _spec(expiry: date, first: date, last: date) -> ExpirySpec:
    return ExpirySpec(expiry, 50, SRC, first, last, 1000, 50)


REAL_2023 = [
    _spec(date(2023, 6, 22), date(2023, 5, 1), date(2023, 6, 22)),
    _spec(date(2023, 6, 28), date(2023, 6, 28), date(2023, 6, 28)),  # only its own day
    _spec(date(2023, 6, 29), date(2019, 2, 11), date(2023, 6, 27)),  # stopped 06-27
    _spec(date(2023, 7, 6), date(2023, 5, 1), date(2023, 7, 6)),
]


def test_real_2023_move_is_found() -> None:
    assert expiry_relabels(REAL_2023) == {date(2023, 6, 29): date(2023, 6, 28)}


def test_normal_expiries_have_no_relabel() -> None:
    assert expiry_relabels([REAL_2023[0], REAL_2023[3]]) == {}


def test_long_dated_contract_that_stopped_months_earlier_is_not_a_move() -> None:
    stale = _spec(date(2025, 9, 25), date(2021, 1, 1), date(2025, 7, 31))
    one_day = _spec(date(2025, 9, 24), date(2025, 9, 24), date(2025, 9, 24))
    assert expiry_relabels([stale, one_day]) == {}


def test_listed_expiry_more_than_a_week_later_is_not_a_move() -> None:
    one_day = _spec(date(2023, 6, 28), date(2023, 6, 28), date(2023, 6, 28))
    far = _spec(date(2023, 7, 6), date(2023, 5, 1), date(2023, 6, 27))
    assert expiry_relabels([one_day, far]) == {}


def test_ambiguous_move_fails_loudly() -> None:
    extra = _spec(date(2023, 6, 30), date(2023, 5, 1), date(2023, 6, 26))
    with pytest.raises(DataError, match="several"):
        expiry_relabels([*REAL_2023, extra])
