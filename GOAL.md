# Goal (draft v1)

## Primary goal
Earn **40% per year** from option selling using margin from **pledged mutual funds**,
while the MF portfolio stays invested.

## Weekly target
- Target **up to 1% per week** on trading capital. 1% is the ceiling, not the minimum:
  once the week's target is hit, stop adding risk.
- 40% / ~50 trading weeks = **~0.8% average per week needed**, after losing weeks.

## Implication: losses must be small
With wins capped at 1%, one big loss wipes out many weeks. Roughly:
- 42 weeks at +1% and 10 weeks at -0.2% → ~40% ✅
- 1 week at -10% → erases ~10 winning weeks ❌

So the strategy must cap the downside hard (defined-risk structures, strict stops, sizing).

## Constraints
- Max weekly loss: **TBD** (proposed: -1%)
- Max drawdown: **TBD**
- Never be forced to sell MF units because of margin shortfall.
- Respect the 50:50 cash/collateral rule (keep cash or liquid ETF for the cash portion).
- Every trade follows written, backtested rules: entry, exit, adjustment, position size.

## Open questions
- Market/instruments (Nifty / BankNifty / stocks), broker
- Capital: MF value, post-haircut margin, cash available
- Return base: margin used vs total MF value; pre- or post-cost/tax
- How MACD (1D) is currently used, and trade history
- Naked vs defined-risk; intraday monitoring possible?; weekly vs monthly expiry
