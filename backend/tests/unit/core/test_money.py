from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fintrade.core.errors import InvalidInputError
from fintrade.core.money import from_paise, round_rupees, rupees, to_paise


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("42.50", Decimal("42.50")), (50000, Decimal(50000)), (Decimal("0.05"), Decimal("0.05"))],
)
def test_rupees_accepts_exact_types(raw: str | int | Decimal, expected: Decimal) -> None:
    assert rupees(raw) == expected


@pytest.mark.parametrize("raw", [42.5, True, None, [1]])
def test_rupees_rejects_float_bool_and_other_types(raw: object) -> None:
    with pytest.raises(InvalidInputError, match="unsupported money type"):
        rupees(raw)  # type: ignore[arg-type]


@pytest.mark.parametrize("raw", ["abc", "", "1,000"])
def test_rupees_rejects_non_numbers(raw: str) -> None:
    with pytest.raises(InvalidInputError, match="not a number"):
        rupees(raw)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_rupees_rejects_non_finite(raw: str) -> None:
    with pytest.raises(InvalidInputError, match="finite"):
        rupees(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("10.005", "10.01"), ("10.004", "10.00"), ("-10.005", "-10.01"), ("7", "7.00")],
)
def test_round_rupees_half_up_to_paise(raw: str, expected: str) -> None:
    assert round_rupees(Decimal(raw)) == Decimal(expected)


def test_to_paise_and_back() -> None:
    assert to_paise(Decimal("42.50")) == 4250
    assert from_paise(4250) == Decimal("42.50")
    assert to_paise(Decimal(-1)) == -100


def test_to_paise_rejects_fractional_paise() -> None:
    with pytest.raises(InvalidInputError, match="fractional paise"):
        to_paise(Decimal("0.001"))


@pytest.mark.parametrize("raw", [True, 1.0, "100"])
def test_from_paise_rejects_non_int(raw: object) -> None:
    with pytest.raises(InvalidInputError, match="paise must be int"):
        from_paise(raw)  # type: ignore[arg-type]


@given(st.integers(min_value=-(10**12), max_value=10**12))
def test_paise_round_trip_is_exact(paise: int) -> None:
    assert to_paise(from_paise(paise)) == paise
