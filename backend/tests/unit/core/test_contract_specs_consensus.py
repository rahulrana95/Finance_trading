"""resolve_with_neighbours: real cases from the full 2019-2026 history."""

from datetime import date

from fintrade.core.contract_specs import ExpirySpec, LotSizeSource, resolve_with_neighbours

INF, STA, UNK, CON = (
    LotSizeSource.INFERRED,
    LotSizeSource.STATED,
    LotSizeSource.UNKNOWN,
    LotSizeSource.CONSENSUS,
)


def _spec(
    expiry: date,
    lot: int | None,
    source: LotSizeSource,
    *,
    first: date | None = None,
    observations: int = 2000,
) -> ExpirySpec:
    """A spec traded from 30 days before expiry (a typical weekly) unless told otherwise."""
    start = first or date.fromordinal(expiry.toordinal() - 30)
    return ExpirySpec(expiry, lot, source, start, expiry, observations, lot)


def _lots(specs: list[ExpirySpec]) -> list[tuple[int | None, LotSizeSource]]:
    return [(s.lot_size, s.source) for s in specs]


def test_long_dated_monthly_dragged_down_by_old_positions_is_fixed() -> None:
    # 2021-09-30 monthly came out as 25 while its weekly neighbours were 50.
    specs = [
        _spec(date(2021, 9, 23), 50, INF),
        _spec(date(2021, 9, 30), 25, INF),
        _spec(date(2021, 10, 7), 50, INF),
    ]
    assert _lots(resolve_with_neighbours(specs)) == [(50, INF), (50, CON), (50, INF)]


def test_unknown_lot_takes_the_neighbours_value() -> None:
    specs = [_spec(date(2023, 3, 23), 50, INF), _spec(date(2023, 3, 30), None, UNK)]
    assert _lots(resolve_with_neighbours(specs))[1] == (50, CON)


def test_stated_values_are_never_changed() -> None:
    # Real case: Jan 2025 monthly kept lot 25 (stated) while new weeklies were 75.
    specs = [
        _spec(date(2025, 1, 23), 75, STA),
        _spec(date(2025, 1, 30), 25, STA),
        _spec(date(2025, 2, 6), 75, STA),
    ]
    assert _lots(resolve_with_neighbours(specs)) == [(75, STA), (25, STA), (75, STA)]


def test_a_real_lot_change_is_not_overwritten() -> None:
    # 75 -> 50 revision: a larger value is not a gcd degradation, so it stays.
    specs = [_spec(date(2021, 7, 22), 75, INF), _spec(date(2021, 7, 29), 50, INF)]
    assert _lots(resolve_with_neighbours(specs)) == [(75, INF), (50, INF)]


def test_disagreeing_neighbours_leave_the_value_alone() -> None:
    specs = [
        _spec(date(2024, 4, 18), 50, INF),
        _spec(date(2024, 4, 25), 25, INF),
        _spec(date(2024, 5, 2), 25, INF),
    ]
    assert _lots(resolve_with_neighbours(specs))[1] == (25, INF)


def test_neighbours_beyond_seven_days_are_ignored() -> None:
    specs = [_spec(date(2021, 9, 22), 50, INF), _spec(date(2021, 9, 30), 25, INF)]
    assert _lots(resolve_with_neighbours(specs))[1] == (25, INF)


def test_value_that_does_not_divide_the_market_lot_is_kept() -> None:
    specs = [_spec(date(2026, 1, 6), 65, INF), _spec(date(2026, 1, 13), 75, INF)]
    assert _lots(resolve_with_neighbours(specs)) == [(65, INF), (75, INF)]


def test_unknown_neighbours_do_not_vote() -> None:
    specs = [_spec(date(2023, 3, 23), None, UNK), _spec(date(2023, 3, 30), None, UNK)]
    assert _lots(resolve_with_neighbours(specs)) == [(None, UNK), (None, UNK)]


def test_holiday_moved_long_dated_pair_is_fixed_by_reliable_weeklies() -> None:
    # Real case: the June 2023 monthly (listed 2019) moved from Thu 29th to Wed 28th
    # for a holiday; both dates carry stale 25-lot positions and vote for each other.
    old = date(2019, 2, 11)
    specs = [
        _spec(date(2023, 6, 22), 50, INF),
        _spec(date(2023, 6, 28), 25, INF, first=date(2023, 6, 28), observations=398),
        _spec(date(2023, 6, 29), 25, INF, first=old, observations=3689),
        _spec(date(2023, 7, 6), 50, INF),
    ]
    assert _lots(resolve_with_neighbours(specs)) == [(50, INF), (50, CON), (50, CON), (50, INF)]


def test_voter_reliability_rules() -> None:
    weekly = _spec(date(2023, 7, 6), 50, INF)
    assert weekly.is_reliable_voter
    assert not _spec(
        date(2023, 7, 6), 50, INF, first=date(2023, 3, 7)
    ).is_reliable_voter  # 121 days
    assert _spec(date(2023, 7, 6), 50, INF, first=date(2023, 3, 8)).is_reliable_voter  # 120 days
    assert not _spec(date(2023, 7, 6), 50, INF, observations=999).is_reliable_voter
    assert _spec(date(2030, 6, 25), 65, STA, first=date(2025, 1, 1)).is_reliable_voter
    assert not _spec(date(2023, 7, 6), None, UNK).is_reliable_voter
    assert not _spec(date(2023, 7, 6), 50, CON).is_reliable_voter


def test_expired_as_listed() -> None:
    moved = ExpirySpec(date(2023, 6, 29), 50, INF, date(2019, 2, 11), date(2023, 6, 27), 3689, 25)
    assert not moved.expired_as_listed
    assert _spec(date(2023, 6, 28), 50, INF).expired_as_listed
