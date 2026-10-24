from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest

from fintrade.core.errors import InvalidInputError
from fintrade.core.timezone import IST, ensure_ist


def test_utc_converts_to_ist() -> None:
    result = ensure_ist(datetime(2026, 10, 27, 4, 30, tzinfo=UTC))
    assert result == datetime(2026, 10, 27, 10, 0, tzinfo=IST)
    assert result.utcoffset() == timedelta(hours=5, minutes=30)


def test_ist_input_unchanged() -> None:
    moment = datetime(2026, 10, 27, 10, 0, tzinfo=IST)
    assert ensure_ist(moment) == moment


def test_other_offset_converts() -> None:
    new_york = timezone(timedelta(hours=-4))
    result = ensure_ist(datetime(2026, 10, 26, 23, 0, tzinfo=new_york))
    assert (result.hour, result.minute) == (8, 30)


def test_naive_datetime_rejected() -> None:
    with pytest.raises(InvalidInputError, match="naive"):
        ensure_ist(datetime(2026, 10, 27, 10, 0))  # noqa: DTZ001 - testing the rejection


class _BrokenTz(tzinfo):
    def utcoffset(self, _dt: datetime | None) -> None:
        return None

    def dst(self, _dt: datetime | None) -> None:
        return None

    def tzname(self, _dt: datetime | None) -> None:
        return None


def test_tzinfo_without_offset_rejected() -> None:
    with pytest.raises(InvalidInputError):
        ensure_ist(datetime(2026, 10, 27, 10, 0, tzinfo=_BrokenTz()))
