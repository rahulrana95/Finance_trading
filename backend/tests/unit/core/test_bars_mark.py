"""Mark price: NSE reports settle 0 for some far strikes that still have a close."""

from decimal import Decimal

from tests.support.bars import make_bar


def test_mark_is_settle_when_reported() -> None:
    assert make_bar(settle=Decimal("4.20"), close=Decimal("4.65")).mark == Decimal("4.20")


def test_mark_falls_back_to_close_when_settle_is_zero() -> None:
    assert make_bar(settle=Decimal(0), close=Decimal("4.65")).mark == Decimal("4.65")
