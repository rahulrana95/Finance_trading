# Goal (v2)

## Capital
- Total MF portfolio: ₹1 Cr (stays invested, pledged for margin)
- Trading capital: **₹50 L** (all % below are on ₹50 L)
- Respect the 50:50 cash/collateral rule (keep the cash portion in cash or a liquid ETF).
- Never be forced to sell MF units because of a margin shortfall.

## Returns
| | % | ₹ |
|---|---|---|
| Stretch target / year | 40% | ₹20 L |
| Minimum acceptable / year | 10% | ₹5 L |
| Max profit target / week | 1% | ₹50 K |

Once the week's 1% target is hit, stop adding risk for that week.

## Risk limits (hard rules, these override the return targets)
| | % | ₹ |
|---|---|---|
| Max loss / week | 1% (proposed) | ₹50 K |
| Max drawdown / month | 3% | ₹1.5 L |
| Max drawdown / year | 5% | ₹2.5 L |

If a limit is hit: stop trading for the rest of that period and review.

**Core principle:** option selling wins ~80–90% of the time. The goal is to make the
10–20% losing trades **small and capped**, not to win more often.

## Instruments and style
- Nifty 50 index options only, weekly expiry (Tuesday), lot size 65
- Defined risk only, no naked short options:
  - Iron condor (range view)
  - Bear call spread (bearish view)
  - Bull put spread (bullish view)
- Short strikes at delta ≤ 0.12 (≈88%+ probability of expiring OTM)
- Option buying allowed later if the backtest supports it
- Directional bias: MACD (1D), to be validated in the backtest
- Monitoring: end of day, 1–2 checks per day max

## System
1. **Backtest engine:** test the rules on historical Nifty options data.
2. **Daily suggestion:** every trading day, generate the day's decision (including "do nothing") and log it.
3. **Review loop:** score each suggestion as right or wrong and log why.
4. **Learning:** use the logged results to tune the rules (ML/RL later, once enough data exists).
5. **Live deployment:** later, after the backtest and paper trading pass.

Data/API candidate: DhanHQ (live feed + option chain with Greeks). To be verified.

## Decisions made
- Entries always use next week's expiry
- Weekly loss limit: 1% (₹50 K)
- One decision every trading day (including "do nothing"), not just Mondays
- Live P&L check every 30 min for all open positions

## Related docs
- `AGENTS.md`: global guardrails (highest authority)
- `ARCHITECTURE.md`: system design, brokers, storage, alerts
- `RULES.md`: global rules
- `MONITORING.md`: live P&L tracking
- `ML.md`: prediction models stacked on top of the rules
- `RL.md`: what the RL system needs

## Open questions
- Source for historical options data for the backtest
