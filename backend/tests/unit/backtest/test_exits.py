"""Rule exits on daily bars: core.rules.exits fed from the day's chain."""

from datetime import date
from decimal import Decimal

import pytest

from fintrade.backtest.data import InMemoryMarketData
from fintrade.backtest.exits import RuleExitPolicy
from fintrade.backtest.trades import OpenTrade, Ticket, open_trade
from fintrade.core.errors import InvalidInputError
from fintrade.core.rules.strategy_config import ExitConfig
from tests.support.backtest import SettleFill
from tests.support.calendar import expiry_calendar
from tests.support.chain import FORWARD, chain_history
from tests.support.instruments import EXPIRY, bull_put

MON, TUE, DEADLINE = date(2026, 10, 26), date(2026, 10, 27), date(2026, 11, 2)
STRIKES = range(23000, 27550, 50)
NEVER = ExitConfig(profit_target_pct_of_max=Decimal(100), stop_loss_multiple_of_credit=Decimal(50))


def _setup(forwards: dict[date, float]) -> tuple[InMemoryMarketData, OpenTrade]:
    data = InMemoryMarketData(chain_history({MON: FORWARD, **forwards}, EXPIRY, STRIKES))
    ticket = Ticket(1, bull_put(), 65, Decimal(0))
    return data, open_trade(ticket, MON, data.option_bars(MON), SettleFill())


def _reasons(config: ExitConfig, day: date, forward: float, limit: bool = False) -> list[str]:
    data, trade = _setup({day: forward})
    policy = RuleExitPolicy(expiry_calendar(), config)
    return policy.reasons(trade, day, data.option_bars(day), limit)


def test_holds_when_no_rule_applies() -> None:
    assert _reasons(NEVER, TUE, FORWARD) == []


def test_profit_target_from_time_decay() -> None:
    config = ExitConfig(profit_target_pct_of_max=Decimal(1))
    assert _reasons(config, TUE, FORWARD) == ["profit_target"]


def test_forward_below_short_put_is_a_touch() -> None:
    assert _reasons(NEVER, TUE, 24590.0) == ["strike_touched"]


def test_stop_loss_on_a_fall() -> None:
    reasons = _reasons(ExitConfig(), TUE, 24700.0)
    assert reasons == ["stop_loss"]


def test_time_exit_on_the_deadline_day_close() -> None:
    assert _reasons(NEVER, DEADLINE, FORWARD) == ["time_exit"]


def test_loss_limit_flag_forces_exit() -> None:
    assert _reasons(NEVER, TUE, FORWARD, limit=True) == ["loss_limit_hit"]


def test_still_open_on_expiry_day_fails_loudly() -> None:
    data, trade = _setup({EXPIRY: FORWARD + 1})
    with pytest.raises(InvalidInputError):
        RuleExitPolicy(expiry_calendar()).reasons(trade, EXPIRY, data.option_bars(EXPIRY), False)
