# ML Layer: Predictions on Top of the Rules

## Key idea: stack, don't replace

We do **not** build one big model that decides everything. We stack layers. Each layer
must prove it beats the layer below before it is used.

```
 AGENTS.md / RULES.md guardrails   ← always on top, cannot be overridden
            ▲
 L3  Bandit / RL (later)            ← chooses among allowed actions (RL.md)
            ▲
 L2  Meta-model: TAKE or SKIP, and size
            ▲
 L1  Forecast models: range, volatility, touch probability
            ▲
 L0  Rules engine: proposes candidate trades (MACD + trend + delta ≤ 0.12)
```

- **L0 (existing rules)** proposes trades. It is the baseline.
- **L1** forecasts what matters for option selling.
- **L2** looks at each L0 trade plus the L1 forecasts and answers: *"Will this trade
  work?"* Skip it, take it, or take it smaller. This method is called **meta-labeling**.
- **L3** comes later (see `RL.md`).

Why this design: the rules already win ~88% of the time at ≤ 0.12 delta. The ML job is
**not** to win more often in general. It is to **spot the 12% losers in advance and skip
or shrink them.** That is how we cut the rare big losses.

## 1. What to predict (easiest and most useful first)

| # | Target | Why it matters | Difficulty |
|---|---|---|---|
| 1 | **Realized volatility** over the trade's life vs implied volatility (IV) | If IV > expected realized vol, premium is rich: good to sell | Medium (vol is fairly predictable) |
| 2 | **Range**: 5th and 95th percentile of Nifty until expiry | Put short strikes outside the likely range | Medium |
| 3 | **Touch probability**: chance spot touches each short strike before exit | Directly predicts losers | Medium |
| 4 | **Meta-label**: chance this exact trade hits the profit target before the stop or time exit | Final TAKE / SKIP / size decision | Medium |
| 5 | Direction (up / down) | Only used as a feature. Hardest to predict, so never trusted alone | Hard |

Volatility and range can be predicted much more reliably than direction, and option
selling profits depend mostly on them.

## 2. Models (simple first)

| Stage | Models | Use |
|---|---|---|
| Baseline | Rules only; GARCH / HAR for volatility | Benchmark to beat |
| Main | Logistic regression, gradient boosting (LightGBM / XGBoost), quantile regression | L1 and L2 |
| Later | Small neural nets (LSTM / temporal CNN); pre-trained time-series models (e.g. Chronos, TimesFM) as **extra features only** | Only if they beat the main models out of sample |

Gradient boosting on good features usually beats deep learning on this much data
(~1,500–2,500 daily samples). Deep models come only after the simple ones are proven.

### Regime filter (HMM)

A Hidden Markov Model (`hmmlearn`) on daily Nifty returns, range and VIX classifies each
day into 3 regimes. The regime picks the structure; it never raises risk:

| Regime | Allowed action |
|---|---|
| Sideways / mean-reverting | Iron condor (normal size) |
| Trending | Credit spread on the trend side only (bull put in uptrend, bear call in downtrend) |
| High-vol expansion | Smaller size, wider wings, or `NO_ACTION` |

- Use **filtered** regime probabilities (past data only). Never the Viterbi path or
  smoothed probabilities over the full history: those use future data.
- If the regime probability is unclear (no regime > ~60%), treat it as high-vol.

## 3. Features

Same state as `RL.md`, plus:
- IV minus forecast realized vol (volatility risk premium)
- Distance of each short strike from spot, in ATR and in expected-move units
- Recent gap frequency, overnight return size
- Global cues before open: GIFT Nifty, US index futures, USD/INR, crude
- FII / DII flows, PCR change, OI build-up at the short strikes
- Event flag and days to next event
- PCR momentum, speed of OI shift / unwinding at the short strikes, max pain distance
- HMM regime probabilities (filtered)
- Distance of short strikes from the nearest order block (Smart Money Concepts). Test only;
  must be shifted by the swing length to avoid look-ahead (see `ARCHITECTURE.md`)

## 4. Making predictions reliable

"Accurate" alone is misleading: a model that always says "win" is already 88% accurate.
So we measure what actually matters.

**a. Right metrics**
- Of the trades the model **skips**, how many would have lost? (Is it removing losers?)
- Worst trade, worst week, worst month vs rules-only
- Average loss of losing trades, total P&L after costs
- **Calibration:** when the model says 90%, it should win ~90% of the time. Checked with
  a reliability chart and Brier score, and fixed with calibration (isotonic / Platt).

**b. Honest testing**
- Walk-forward only (train on the past, test on the next period).
- **Purging + embargo:** trades overlap in time, so remove training samples that overlap
  the test period. Otherwise the results look better than reality.
- Test on stress periods: March 2020, June 2024 election day, big gap days.
- Never pick the model with the best score after trying 100 variants. Count how many
  variants were tried and require a bigger margin when many were tried.

**c. Know when not to trust it**
- **Abstain:** if the model is uncertain (probability in a grey zone, or models disagree),
  the answer is `NO_ACTION` or a smaller size, never a bigger one.
- **Conformal prediction** for the range forecast: gives a range with a tested coverage
  (e.g. "95% of the time Nifty stayed inside this band"). Short strikes go outside it.
- **Ensemble:** use several models. Take the trade only when they agree.

**d. Watch it live**
- Track live calibration and feature drift every week.
- If calibration or performance degrades past a set threshold, **fall back to
  rules-only automatically** and alert the owner.
- **Shadow mode first:** a new model runs alongside the live one and logs its suggestions
  without trading, for at least 8 weeks.
- **Champion / challenger:** the challenger replaces the champion only if it wins out of
  sample and the owner approves.

## 5. System reliability (data and infrastructure)

- **Two data sources:** primary (DhanHQ) plus a backup (NSE data or a second broker).
  Cross-check prices. If they disagree beyond a threshold, no new orders.
- **Stale data:** data older than 5 min in market hours means no new orders (fail closed).
- **Heartbeat:** monitoring sends a heartbeat every 30 min. A missed heartbeat alerts the owner.
- **Ledger reconciliation** every 30 min (`MONITORING.md`).
- **Market calendar:** NSE holidays and shifted expiries handled correctly.
- **All times in IST.**
- **Tests:** every guardrail has an automated test; every model has a reproducible
  training run (fixed data snapshot, fixed seed, saved version).

## 6. When the ML layer is accepted

The L1 + L2 layers are used only if, compared with rules-only, in **every** walk-forward
test year:
- Worst week and worst month are smaller
- Number of losing trades is lower
- Total return after costs is the same or better
- Predictions are well calibrated
- All `AGENTS.md` limits are respected

Otherwise we stay on rules-only and keep collecting data.

## 7. Build order

1. Rules-only backtest (L0): get the baseline numbers.
2. Volatility and range forecasts (L1): check they beat GARCH / simple baselines.
3. Meta-model (L2): TAKE / SKIP / size on top of L0 + L1.
4. Shadow mode live for 4+ weeks.
5. Paper trading, then live with the owner's approval.
6. Bandit / RL (L3) only after L2 is proven.
