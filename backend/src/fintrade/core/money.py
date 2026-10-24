"""Money is never a float (ENGINEERING.md section 5). Rupee amounts are `Decimal`."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from fintrade.core.errors import InvalidInputError

type Rupees = Decimal

PAISE_PER_RUPEE = 100
_PAISE = Decimal("0.01")


def rupees(value: str | int | Decimal) -> Rupees:
    """Parse a rupee amount. Floats and bools are rejected because they lose precision."""
    if isinstance(value, bool) or not isinstance(value, str | int | Decimal):
        raise InvalidInputError(f"unsupported money type: {type(value).__name__}")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise InvalidInputError(f"not a number: {value!r}") from exc
    if not amount.is_finite():
        raise InvalidInputError(f"money must be finite: {value!r}")
    return amount


def round_rupees(amount: Rupees) -> Rupees:
    """Round to whole paise, half up (how brokers round charges)."""
    return amount.quantize(_PAISE, rounding=ROUND_HALF_UP)


def to_paise(amount: Rupees) -> int:
    """Convert rupees to integer paise. Amounts with fractional paise are rejected."""
    paise = amount * PAISE_PER_RUPEE
    if paise != paise.to_integral_value():
        raise InvalidInputError(f"fractional paise: {amount}")
    return int(paise)


def from_paise(paise: int) -> Rupees:
    """Convert integer paise to rupees."""
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise InvalidInputError(f"paise must be int: {type(paise).__name__}")
    return Decimal(paise) / PAISE_PER_RUPEE
