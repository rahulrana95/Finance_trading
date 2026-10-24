"""Backtest metrics. AGENTS.md section 5: drawdown, worst week/month and trade count are
always reported next to the return."""

from datetime import date
from decimal import Decimal

import pytest

from fintrade.backtest.metrics import PeriodPnl, compute_metrics, format_report
from fintrade.core.errors import InvalidInputError
from fintrade.core.risk.budget import DailyPnl
from tests.support.backtest import closed_with_pnl

CAPITAL = Decimal(1_000_000)
# equity path: +5k, -10k (peak 5k -> dd 15k), +2k, then a new month +20k
DAILY = [
    DailyPnl(date(2026, 9, 28), Decimal(5000), Decimal(0)),  # Mon, week 40
    DailyPnl(date(2026, 9, 30), Decimal(-10000), Decimal(0)),  # Wed, week 40
    DailyPnl(date(2026, 10, 5), Decimal(-10000), Decimal(12000)),  # Mon, week 41: eq 2k
    DailyPnl(date(2026, 10, 30), Decimal(22000), Decimal(0)),  # Fri, week 44
]
TRADES = [
    closed_with_pnl(Decimal(5000), costs=Decimal(100)),
    closed_with_pnl(Decimal(-15000), costs=Decimal(100)),
    closed_with_pnl(Decimal(32000), costs=Decimal(100)),
]


def test_returns_and_drawdown() -> None:
    m = compute_metrics(CAPITAL, DAILY, TRADES)
    assert (m.start, m.end) == (date(2026, 9, 28), date(2026, 10, 30))
    assert m.net_pnl == Decimal(22000)
    assert m.return_pct == Decimal("2.2")
    assert m.annualized_return_pct == Decimal("2.2") * 365 / 33
    assert m.max_drawdown == Decimal(15000)
    assert m.max_drawdown_pct == Decimal("1.5")


def test_worst_week_and_month() -> None:
    m = compute_metrics(CAPITAL, DAILY, TRADES)
    assert m.worst_week == PeriodPnl("2026-W40", Decimal(-10000))
    assert m.worst_month == PeriodPnl("2026-09", Decimal(-10000))
    assert m.weeks_at_or_over_loss_limit == 1  # -10k is the 1% weekly limit


def test_trade_statistics() -> None:
    m = compute_metrics(CAPITAL, DAILY, TRADES)
    assert (m.trades, m.wins, m.losses) == (3, 2, 1)
    assert m.win_rate_pct == pytest.approx(Decimal("66.67"), abs=Decimal("0.01"))
    assert m.avg_win == Decimal(18300)  # (4,800 + 31,800) / 2: each trade pays 200 costs
    assert m.avg_loss == Decimal(-15200)
    assert m.total_costs == Decimal(600)
    assert m.profit_factor == Decimal(36600) / Decimal(15200)


def test_no_trades_and_no_losses() -> None:
    m = compute_metrics(CAPITAL, DAILY[:1], [])
    assert (m.trades, m.win_rate_pct, m.avg_win, m.avg_loss, m.profit_factor) == (
        0, None, None, None, None,
    )  # fmt: skip
    m = compute_metrics(CAPITAL, DAILY[:1], TRADES[:1])
    assert (m.avg_loss, m.profit_factor) == (None, None)
    assert m.max_drawdown == 0


def test_breakeven_trade_is_neither_win_nor_loss() -> None:
    m = compute_metrics(CAPITAL, DAILY, [closed_with_pnl(Decimal(200), costs=Decimal(100))])
    assert (m.trades, m.wins, m.losses, m.win_rate_pct) == (1, 0, 0, Decimal(0))


def test_report_always_shows_risk_next_to_return() -> None:
    text = format_report(compute_metrics(CAPITAL, DAILY, TRADES))
    for needle in ("Return", "+2.20%", "Max drawdown", "1.50%", "Worst week", "2026-W40",
                   "Worst month", "2026-09", "Trades", "3", "not a guarantee"):  # fmt: skip
        assert needle in text


def test_report_without_trades() -> None:
    text = format_report(compute_metrics(CAPITAL, DAILY[:1], []))
    assert "Win rate: n/a" in text


@pytest.mark.parametrize(
    ("capital", "daily"),
    [
        (Decimal(0), DAILY),
        (Decimal("NaN"), DAILY),
        (CAPITAL, []),
        (CAPITAL, [DAILY[1], DAILY[0]]),
        (CAPITAL, [DAILY[0], DAILY[0]]),
    ],
)
def test_invalid_inputs(capital: Decimal, daily: list[DailyPnl]) -> None:
    with pytest.raises(InvalidInputError):
        compute_metrics(capital, daily, [])
