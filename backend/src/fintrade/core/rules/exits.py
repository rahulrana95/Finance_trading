"""Exit rules for an open position (RULES.md section 4). Whichever comes first closes it.

All reasons that apply are returned, so the journal records why a position was closed.
Hard stops are always rules (ARCHITECTURE.md section 4): an ML exit score may only add an
earlier exit elsewhere, never remove one of these.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fintrade.core.bars import OptionType
from fintrade.core.instruments import Position, Side
from fintrade.core.money import Rupees
from fintrade.core.rules.strategy_config import DEFAULT_EXIT, ExitConfig
from fintrade.core.timezone import ensure_ist

_PCT = Decimal(100)


class ExitReason(StrEnum):
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    STRIKE_TOUCHED = "strike_touched"
    TIME_EXIT = "time_exit"
    LOSS_LIMIT_HIT = "loss_limit_hit"


@dataclass(frozen=True, slots=True)
class ExitInputs:
    position: Position
    max_profit: Rupees  # credit x units, from core.pnl.risk
    open_pnl: Rupees  # mark-to-market, from core.pnl
    spot: Decimal
    now: datetime
    exit_deadline: datetime  # from ExpiryCalendar.exit_deadline
    loss_limit_hit: bool  # from core.risk.budget


def exit_reasons(inputs: ExitInputs, config: ExitConfig = DEFAULT_EXIT) -> list[ExitReason]:
    """Empty list = hold. Any reason = close the whole position now."""
    reasons: list[ExitReason] = []
    if inputs.max_profit > 0:
        target = inputs.max_profit * config.profit_target_pct_of_max / _PCT
        if inputs.open_pnl >= target:
            reasons.append(ExitReason.PROFIT_TARGET)
    stop = -inputs.max_profit.copy_abs() * config.stop_loss_multiple_of_credit
    if inputs.open_pnl <= stop:
        reasons.append(ExitReason.STOP_LOSS)
    if _short_strike_touched(inputs.position, inputs.spot):
        reasons.append(ExitReason.STRIKE_TOUCHED)
    if ensure_ist(inputs.now) >= ensure_ist(inputs.exit_deadline):
        reasons.append(ExitReason.TIME_EXIT)
    if inputs.loss_limit_hit:
        reasons.append(ExitReason.LOSS_LIMIT_HIT)
    return reasons


def _short_strike_touched(position: Position, spot: Decimal) -> bool:
    for leg in position.legs:
        if leg.side is not Side.SELL:
            continue
        strike = leg.contract.strike
        if leg.contract.option_type is OptionType.PUT and spot <= strike:
            return True
        if leg.contract.option_type is OptionType.CALL and spot >= strike:
            return True
    return False
