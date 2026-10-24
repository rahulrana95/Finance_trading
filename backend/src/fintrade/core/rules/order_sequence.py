"""Safe leg order (AGENTS.md section 2): a short option is never unhedged, even briefly.

Entry: buy every hedge before selling any short leg.
Exit: buy back every short leg before selling any hedge.
"""

from fintrade.core.instruments import Leg, Position, Side


def entry_sequence(position: Position) -> list[Leg]:
    """Opening orders: BUY hedges first, then SELL shorts."""
    legs = position.legs
    return [leg for leg in legs if leg.side is Side.BUY] + [
        leg for leg in legs if leg.side is Side.SELL
    ]


def exit_sequence(position: Position) -> list[Leg]:
    """Closing orders: buy back shorts first, then sell hedges.

    The returned legs are the OPEN legs; the closing order for each is the opposite side.
    """
    legs = position.legs
    return [leg for leg in legs if leg.side is Side.SELL] + [
        leg for leg in legs if leg.side is Side.BUY
    ]
