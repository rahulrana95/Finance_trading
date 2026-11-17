"""The stepped buying plan and the choice between shares and futures. Pure."""

from dataclasses import dataclass

from steady.constants import (
    BUY_LEVELS_PCT,
    FUTURES_FROM_STEP,
    INSTRUMENT_CASH,
    INSTRUMENT_FUTURE,
    NOTE_FUTURES_FROM,
    NOTE_FUTURES_USED,
    NOTE_LOT_TOO_BIG,
    NOTE_LOT_UNKNOWN,
    PLAN_PARTS,
    TYPE_COMBO,
)
from steady.core.zones import level_price, zone
from steady.utils.format import inr


@dataclass(frozen=True)
class PlanInput:
    reference_high: float
    last_price: float
    below_pct: float
    capital: float
    per_stock_cap_pct: float
    approved_count: int
    lot_size: int | None
    filled_steps: frozenset[int] = frozenset()
    levels: tuple[float, ...] = BUY_LEVELS_PCT
    parts: tuple[int, ...] = PLAN_PARTS
    futures_from_step: int = FUTURES_FROM_STEP


@dataclass(frozen=True)
class PlanStep:
    step: int
    level_pct: float
    level_price: float
    amount: int
    instrument: str
    quantity: int
    reached: bool
    filled: bool


@dataclass(frozen=True)
class Plan:
    allocation: int
    steps: tuple[PlanStep, ...]
    instrument_type: str
    futures_note: str


def _instrument(p: PlanInput, step: int, amount: int) -> tuple[str, int, str | None]:
    """(instrument, quantity, note) for one step. Futures only if one whole lot fits."""
    shares = (INSTRUMENT_CASH, int(amount // p.last_price))
    if step < p.futures_from_step:
        return (*shares, None)
    if p.lot_size is None:
        return (*shares, NOTE_LOT_UNKNOWN)
    lot_value = p.lot_size * p.last_price
    if lot_value > amount:
        return (*shares, NOTE_LOT_TOO_BIG.format(lot=inr(lot_value), amount=inr(amount)))
    return INSTRUMENT_FUTURE, p.lot_size, NOTE_FUTURES_USED.format(step=step)


def build_plan(p: PlanInput) -> Plan:
    cap = p.per_stock_cap_pct / 100 * p.capital
    allocation = int(min(cap, p.capital / max(p.approved_count, 1)))
    reached = zone(p.below_pct, p.levels)
    note = NOTE_FUTURES_FROM.format(step=p.futures_from_step)
    steps = []
    for index, (pct, part) in enumerate(zip(p.levels, p.parts, strict=True), start=1):
        amount = allocation * part // sum(p.parts)
        instrument, quantity, step_note = _instrument(p, index, amount)
        note = step_note or note
        steps.append(
            PlanStep(
                step=index,
                level_pct=pct,
                level_price=level_price(p.reference_high, pct),
                amount=amount,
                instrument=instrument,
                quantity=quantity,
                reached=index <= reached,
                filled=index in p.filled_steps,
            )
        )
    kinds = {s.instrument for s in steps if s.reached and not s.filled} or {INSTRUMENT_CASH}
    return Plan(allocation, tuple(steps), kinds.pop() if len(kinds) == 1 else TYPE_COMBO, note)
