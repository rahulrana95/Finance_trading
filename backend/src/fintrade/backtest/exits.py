"""Rule-based exit policy for the replay engine: `core.rules.exits` on daily bars.

Daily-bar limits, fixed when 1-minute data arrives (T4.7):
- rules are checked once a day at the close, so an intraday stop or touch is not seen
- old bhavcopies carry no spot price, so the parity forward of the trade's expiry stands
  in for spot (they differ by the carry, about 0.1% for a week)
- a time exit due at 15:00 on the deadline day fills at that day's close
"""

from datetime import date, datetime, time
from decimal import Decimal

from fintrade.backtest.data import DECISION_TIME, DEFAULT_RATE, DayBars, chain_points
from fintrade.backtest.trades import OpenTrade, mark_pnl
from fintrade.core.calendar import ExpiryCalendar
from fintrade.core.pricing.black76 import time_to_expiry_years
from fintrade.core.pricing.forward import StrikeQuote, forward_from_chain
from fintrade.core.rules.exits import ExitInputs, exit_reasons
from fintrade.core.rules.strategy_config import DEFAULT_EXIT, ExitConfig
from fintrade.core.timezone import IST


class RuleExitPolicy:
    def __init__(
        self,
        calendar: ExpiryCalendar,
        config: ExitConfig = DEFAULT_EXIT,
        *,
        rate: float = DEFAULT_RATE,
        decision_time: time = DECISION_TIME,
    ) -> None:
        self._calendar = calendar
        self._config = config
        self._rate = rate
        self._decision_time = decision_time

    def reasons(
        self, trade: OpenTrade, day: date, bars: DayBars, loss_limit_hit: bool
    ) -> list[str]:
        expiry = trade.position.expiry
        now = datetime.combine(day, self._decision_time, tzinfo=IST)
        inputs = ExitInputs(
            position=trade.position,
            max_profit=trade.max_profit,
            open_pnl=mark_pnl(trade, bars),
            spot=self._spot(bars, expiry, now),
            now=now,
            exit_deadline=self._calendar.exit_deadline(expiry),
            loss_limit_hit=loss_limit_hit,
        )
        return [str(reason) for reason in exit_reasons(inputs, self._config)]

    def _spot(self, bars: DayBars, expiry: date, now: datetime) -> Decimal:
        quotes = [
            StrikeQuote(float(p.strike), float(p.call), float(p.put))
            for p in chain_points(bars, expiry).values()
            if p.call is not None and p.put is not None
        ]
        years = time_to_expiry_years(now, expiry)
        return Decimal(forward_from_chain(quotes, years, self._rate))
