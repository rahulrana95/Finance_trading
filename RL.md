# What We Need for RL (Reinforcement Learning)

## Key idea

The model **does not replace the rules**. It chooses among the actions the rules allow
(`RULES.md`). If an action would break a rule, it is blocked before the model can pick it.

The model learns only in a **simulator** built from historical data, never with real money.
Live, it only makes suggestions that are logged and reviewed.

## Daily decisions: more data, but with a catch

- Weekly: ~50 decisions a year. Daily: ~250 decisions a year. Daily is clearly better.
- **Catch:** daily decisions are not independent. Monday's and Tuesday's trades on the
  same expiry win or lose together, so 250 daily samples are worth less than 250 truly
  separate samples.
- **Fix:** use many years of historical data in the simulator. 6+ years × 250 days ≈ 1,500+
  decisions, plus 13 snapshots a day for monitoring and exit learning.

## Start simple: contextual bandit, then full RL

| Step | Method | What it learns |
|---|---|---|
| 1 | Rules only (baseline) | Nothing. Gives the benchmark to beat |
| 2 | Contextual bandit | "Given today's market, which entry action is best?" Reward is that trade's final P&L. Needs much less data |
| 3 | Full RL | Entries and exits/adjustments together, with the effect of open positions on future choices |

Move to the next step only if it beats the previous one **out of sample**.

## 1. State (what the model sees each day)

**Market**
- Nifty spot, daily returns (1, 5, 20 days)
- Trend: MACD (1D) line / signal / histogram, EMA 20 / 50 / 200 position
- Range: ATR, distance from recent high / low
- Volatility: India VIX, VIX change, ATM IV, IV percentile (1 year), IV skew (put vs call)
- Options: put-call ratio, max-OI strikes (support / resistance)
- Calendar: day of week, days to expiry, event flag (RBI / Budget / Fed / election / results)

**Portfolio**
- Number of open positions, their structures and strikes
- Net delta / theta / vega
- Week / month / year P&L
- Remaining loss budgets, margin used %

## 2. Actions (small and discrete)

`NO_ACTION`, `OPEN_IC`, `OPEN_BULL_PUT`, `OPEN_BEAR_CALL`, `ADJUST`, `CLOSE`.

Each `OPEN` also picks from fixed choices:
- Short delta: 0.10 / 0.15 / 0.20
- Wing width: 100 / 150 / 200 points
- Size: 1 / 2 / 3 units (unit size set by the risk budget)

That is ~27 variants per structure. Small enough to learn.

## 3. Reward (what counts as good)

- Base: daily change in portfolio P&L, after all costs.
- Penalty for drawdown: losses count more than gains (e.g. a loss counts 2×).
- Large penalty for getting close to a budget limit.
- Breaching a limit should be impossible (blocked by rules). If the simulator ever shows
  a breach, that is a bug to fix.

This makes the model prefer **steady small profits with no big losses** over high returns
with rare disasters, which is our goal.

## 4. Data needed

| Data | Detail | Purpose |
|---|---|---|
| Nifty spot | Daily + 30-min, 6+ years | State, signals |
| Nifty options prices | All strikes near ATM (±1,500 pts), every expiry, 30-min or better | Simulator |
| India VIX | Daily + intraday | State |
| Greeks / IV | Calculated ourselves (Black-Scholes) from prices | History does not include Greeks |
| Event calendar | RBI, Budget, Fed, elections | Event flag |
| Costs | Brokerage, STT, exchange fees, GST, stamp duty, slippage | Realistic P&L |
| Lot size / expiry history | Lot size and expiry-day changes over time | Correct simulation |

**Regime changes to handle:** Nifty weekly expiry moved from Thursday to Tuesday
(Sept 2025), and lot sizes changed several times. Old data must be mapped correctly.

## 5. The simulator (backtest engine)

The simulator must:
- Replay history day by day and every 30 min
- Apply all `RULES.md` limits and exits exactly as live would
- Fill orders at realistic prices (bid/ask spread + slippage, not mid price)
- Include all costs
- Never use future data (no look-ahead bias)

## 6. Testing (avoid fooling ourselves)

- **Walk-forward:** train on years 1–4, test on year 5; train on 1–5, test on 6; and so on.
- Compare against the rules-only baseline.
- Required stress periods in the test set: March 2020 crash, June 2024 election-day move,
  any other big gap days.
- Pass criteria: meets the `GOAL.md` limits (monthly DD ≤ 3%, yearly DD ≤ 5%) in every
  test year, not just on average.

## 7. Live feedback loop

1. Each morning: the model suggests the day's action and logs it.
2. Paper trade it (Phase 1) or trade it (Phase 2).
3. Monitoring logs a snapshot every 30 min (`MONITORING.md`).
4. After the position closes: the outcome is logged, and a human labels it right / wrong and why.
5. Monthly: add the new data to the simulator, retrain, re-test walk-forward.
   The new model is used only if it beats the current one out of sample.
