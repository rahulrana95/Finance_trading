from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from fintrade.backtest.candidates import Candidate, CandidateConfig, generate_candidates
from fintrade.core.bars import OptionType
from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import CreditSpread, IronCondor, Structure
from fintrade.core.pricing.black76 import greeks
from fintrade.core.pricing.chain import ChainPoint
from fintrade.core.rules.entry import EntryRule, ProposedEntry, check_entry
from tests.support.chain import FORWARD, RATE, VOL, YEARS, chain_bars, flat_chain
from tests.support.rules import good_account

DAY, EXPIRY = date(2026, 10, 26), date(2026, 11, 3)  # exactly 8 days, close to close
STRIKES = range(23000, 27550, 50)
ONE_WIDTH = CandidateConfig(widths=(Decimal(200),))


def _bars(points: list[ChainPoint] | None = None) -> Any:
    return chain_bars(flat_chain(STRIKES) if points is None else points, DAY, EXPIRY)


def _abs_delta(option_type: OptionType, strike: Decimal) -> Decimal:
    return Decimal(abs(greeks(option_type, FORWARD, float(strike), YEARS, RATE, VOL).delta))


def _sides(c: Candidate) -> tuple[CreditSpread, ...]:
    p = c.position
    return (p.put_spread, p.call_spread) if isinstance(p, IronCondor) else (p,)


def test_three_structures_by_three_deltas() -> None:
    found = generate_candidates(DAY, _bars(), EXPIRY, ONE_WIDTH)
    assert [(c.structure, c.target_delta) for c in found] == [
        (s, d) for s in Structure for d in (Decimal("0.08"), Decimal("0.10"), Decimal("0.12"))
    ]
    assert len(generate_candidates(DAY, _bars(), EXPIRY, CandidateConfig())) == 27


def test_short_strike_is_nearest_the_money_without_exceeding_target() -> None:
    step = Decimal(50)
    for c in generate_candidates(DAY, _bars(), EXPIRY, ONE_WIDTH):
        for side in _sides(c):
            kind, strike = side.option_type, side.short.contract.strike
            delta = c.short_deltas[side.short.contract]
            assert delta == pytest.approx(_abs_delta(kind, strike), abs=Decimal("0.002"))
            assert delta <= c.target_delta
            closer = strike + step if kind is OptionType.PUT else strike - step
            assert _abs_delta(kind, closer) > c.target_delta - Decimal("0.002")


def test_hedge_is_width_further_out_same_expiry_and_lots() -> None:
    config = replace(ONE_WIDTH, lots=3)
    for c in generate_candidates(DAY, _bars(), EXPIRY, config):
        assert set(c.short_deltas) == {s.short.contract for s in _sides(c)}
        for side in _sides(c):
            assert side.width == Decimal(200)
            assert side.expiry == EXPIRY
            assert side.lots == 3


def test_every_candidate_passes_the_delta_hard_limit() -> None:
    for c in generate_candidates(DAY, _bars(), EXPIRY, CandidateConfig()):
        entry = ProposedEntry(c.position, c.short_deltas, Decimal(1), Decimal(1), EXPIRY)
        codes = {v.code for v in check_entry(entry, good_account())}
        assert EntryRule.SHORT_DELTA not in codes
        assert EntryRule.MISSING_DELTA not in codes


def test_missing_hedge_bar_drops_only_that_candidate() -> None:
    put_120 = generate_candidates(DAY, _bars(), EXPIRY, ONE_WIDTH)[2]
    assert isinstance(put_120.position, CreditSpread)
    hedge = put_120.position.long.contract.strike
    points = [replace(p, put=None) if p.strike == hedge else p for p in flat_chain(STRIKES)]
    found = generate_candidates(DAY, _bars(points), EXPIRY, ONE_WIDTH)
    assert (Structure.BULL_PUT, Decimal("0.12")) not in [
        (c.structure, c.target_delta) for c in found
    ]
    assert (Structure.IRON_CONDOR, Decimal("0.12")) not in [
        (c.structure, c.target_delta) for c in found
    ]
    assert len(found) == 7


def test_no_strike_below_tiny_target_means_no_candidate() -> None:
    narrow = range(24900, 25550, 50)  # every OTM strike here has |delta| far above 0.001
    config = replace(ONE_WIDTH, target_deltas=(Decimal("0.001"),))
    assert generate_candidates(DAY, _bars(flat_chain(narrow)), EXPIRY, config) == []


def test_other_expiry_and_other_symbol_ignored() -> None:
    other_expiry = chain_bars(flat_chain(STRIKES), DAY, date(2026, 11, 10))
    other_symbol = chain_bars(flat_chain(STRIKES), DAY, EXPIRY, symbol="BANKNIFTY")
    assert generate_candidates(DAY, {**other_expiry, **other_symbol}, EXPIRY, ONE_WIDTH) == []
    found = generate_candidates(DAY, {**other_symbol, **_bars()}, EXPIRY, ONE_WIDTH)
    assert len(found) == 9


@pytest.mark.parametrize(
    "kwargs",
    [
        {"structures": ()},
        {"target_deltas": ()},
        {"widths": ()},
        {"target_deltas": (Decimal(0),)},
        {"target_deltas": (Decimal("0.1201"),)},
        {"widths": (Decimal(0),)},
        {"lots": 0},
        {"rate": float("nan")},
        {"min_price": Decimal(0)},
    ],
)
def test_invalid_config_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises(InvalidInputError):
        CandidateConfig(**kwargs)


def test_hard_limit_delta_itself_is_allowed() -> None:
    assert CandidateConfig(target_deltas=(Decimal("0.12"),)).target_deltas == (Decimal("0.12"),)
