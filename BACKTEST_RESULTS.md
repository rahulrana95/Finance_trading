# Backtest results log

Every result here is a research result, **not a guarantee**. Each entry states its data,
costs and known limits, and the risk next to the return (AGENTS.md sections 5 and 9).
Entries are append-only: later runs are added below, earlier ones are never edited.

---

## 2026-10-24 · First walk-forward, daily bhavcopy, one lot per trade

**Verdict: no edge out of sample. Fails the go / no-go bar (`ARCHITECTURE.md` §12).**

### Setup

| Item | Value |
|---|---|
| Data | NSE F&O bhavcopy, 2019-02-11 to 2026-10-23 (1,898 trading days); entries up to 2026-10-09 |
| Prices | Mark = settle, or close when settle is not reported (T4.2b) |
| Fills | Worse of close / mark, half-spread 2.5% of price (min 2 ticks), 1 tick slippage, rounded against us (T4.2) |
| Costs | Date-aware STT, exchange, SEBI, stamp, IPFT, GST + ₹20 per order (T2.5) |
| Liquidity | Both legs ≥ 100 contracts traded on entry day, 0 < credit < width (T4.3b) |
| Candidates | Bull put, bear call, iron condor × target delta 0.08 / 0.10 / 0.12 × width 100 / 200 / 300 |
| Exits (4 configs) | Profit target 50% / 70% of max × stop 2× / 3× credit; strike touch; time exit 15:00 the day before expiry. Checked once a day at the close |
| Search | Also min credit 0 / 5 / 10% of width. Train 12 months, test the next 3; choose by mean net P&L per trade (≥ 30 training trades) using only trades closed before the test window |
| Sizing | 1 lot per trade, each candidate on its own (no account limits, overlaps not netted) |

46,700 counterfactual trades per exit config; none skipped, none unfinished.

### Out-of-sample result (all test windows, Feb 2020 – Oct 2026)

| Metric | Value |
|---|---|
| Trades | 522 |
| Net P&L | **−₹43,974** (1 lot per trade) |
| Mean per trade | −₹84 |
| Win rate | 78% |
| Worst trade | −₹10,891 |
| Windows with no trade | 4 of 27 |

In-sample (training) scores were +₹200 to +₹1,000 per trade in most windows; out of sample
they were mostly negative. The chosen arm changed between windows (bull put 0.12 / 300 in
2020-21, bear call in 2022 and late 2023, iron condor 0.12 / 300 from 2024). A large gap
between in-sample and out-of-sample with unstable choices is the signature of fitting noise.

Per-window results (chosen arm, in-sample mean, out-of-sample trades and mean):

| Test from | Arm (exit, structure, delta, width, min credit %) | IS ₹/trade | OOS n | OOS ₹/trade |
|---|---|---|---|---|
| 2020-02-11 | pt70_sl3, iron condor, 0.08, 300, 0 | 23 | 21 | −2,089 |
| 2020-05-11 | pt70_sl3, bear call, 0.10, 100, 5 | 35 | 26 | −222 |
| 2020-08-11 | pt70_sl2, bull put, 0.12, 300, 5 | 268 | 3 | 961 |
| 2020-11-11 | pt70_sl2, bull put, 0.12, 300, 5 | 327 | 7 | 648 |
| 2021-02-11 | pt70_sl2, bull put, 0.12, 300, 5 | 381 | 27 | 652 |
| 2021-05-11 | pt70_sl2, bull put, 0.12, 300, 5 | 724 | 3 | 846 |
| 2021-08-11 | pt70_sl2, bull put, 0.12, 300, 5 | 689 | 7 | −282 |
| 2021-11-11 | pt70_sl3, bull put, 0.12, 300, 5 | 537 | 24 | −1,130 |
| 2022-02-11 | pt70_sl3, bear call, 0.12, 300, 5 | 176 | 47 | −99 |
| 2022-05-11 | pt70_sl3, bear call, 0.12, 300, 5 | −32 | 33 | −9 |
| 2022-08-11 | pt50_sl3, iron condor, 0.10, 200, 5 | 275 | 13 | −164 |
| 2022-11-11 | pt50_sl2, iron condor, 0.12, 300, 5 | 270 | 3 | 642 |
| 2023-02-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 347 | 0 | – |
| 2023-05-11 | pt50_sl2, iron condor, 0.12, 300, 5 | 639 | 0 | – |
| 2023-08-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 431 | 0 | – |
| 2023-11-11 | pt70_sl2, bear call, 0.12, 200, 5 | −23 | 37 | −447 |
| 2024-02-11 | pt70_sl3, bull put, 0.12, 300, 0 | −9 | 59 | −118 |
| 2024-05-11 | pt70_sl2, bear call, 0.12, 300, 5 | 485 | 33 | −23 |
| 2024-08-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 727 | 14 | 59 |
| 2024-11-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 554 | 35 | 408 |
| 2025-02-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 525 | 12 | 450 |
| 2025-05-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 331 | 22 | 1,493 |
| 2025-08-11 | pt70_sl3, iron condor, 0.10, 200, 5 | 721 | 0 | – |
| 2025-11-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 774 | 8 | 613 |
| 2026-02-11 | pt70_sl2, iron condor, 0.12, 300, 5 | 1,043 | 31 | −346 |
| 2026-05-11 | pt70_sl2, iron condor, 0.12, 200, 5 | 642 | 52 | −165 |
| 2026-08-11 | pt70_sl3, bear call, 0.12, 300, 5 | 142 | 5 | −462 |

### What limits this result

- **Daily closes are noisy for our strikes.** 20–40% of adjacent thin-strike pairs break
  no-arbitrage, and 4–7% of liquid pairs do (closes are at different times). Credits at
  delta ≤ 0.12 are only ₹5–15, the same size as that noise.
- **Exits are checked once a day.** Intraday stops and touches are missed (both ways).
- **Liquidity cut trade count hard** (100 contracts per leg); some windows had no trade.
- **One lot per trade**: ₹20 per order is large next to a ₹500–1,000 credit.
- **No account-level replay yet** (T4.6b), so no yearly return, drawdown or worst month
  against the ₹50 L capital; the §12 bar cannot be checked line by line.
- No VIX, MACD or event filters yet.

### What it means

Following `ARCHITECTURE.md` §11 ("if the rules-only backtest can't clear the §12 bar after
costs, adding ML or news will not rescue it"), this does not justify paper trading the
strategy as it stands. The cheapest next evidence, in order:

1. **Intraday data** (the 1-minute quote request) to remove close-price noise and model
   stops properly. This result cannot separate "no edge" from "daily data too noisy".
2. **Account-level replay** (T4.6b) with realistic sizing, to state yearly return, max
   drawdown and worst month against the §12 bar.
3. **Simpler, fewer choices** (e.g. iron condor 0.12 / 300 only) to cut overfitting, then
   compare with "always iron condor" and cash as §12 requires.

---

## 2026-11-16 · Market-move research: a "calm score" for the week ahead (T4.8)

**Verdict: the signal is real and repeats in other markets, but the trading rule built on it
earned almost nothing on the 2022-2026 holdout. Not a strategy yet. No 20-30% result found.**

Research only. Option prices here are **modelled from India VIX with an assumed skew**, not
real quotes, so every P&L figure below is an estimate, not a backtest on traded prices.

### Setup

| Item | Value |
|---|---|
| Data | Nifty daily OHLC and India VIX (Yahoo), 2008-04 to 2026-10; S&P 500 / VIX 1990-2026 and Nasdaq 100 / VXN 2001-2026 as independent checks |
| Window | Enter at the open, watch the next 6 sessions |
| Strike distance | 1.28 x VIX-implied move (about 0.10 delta); "touch" = Nifty reached it during the window |
| Split | Train to 2016-12, validation 2017-2021, holdout 2022-01 to 2026-10 (run once, after freezing the rule) |
| Code | `research/2026-11-market-moves/` |

### Findings on market moves (no option prices involved)

- **Direction is not predictable after the open.** MACD, 50-day average, yesterday's move and
  the US overnight move all scored 48.7-50.5% on open-to-close direction (4,580 days). The US
  overnight move predicts the opening gap 68% of the time, which is in the price by 09:15.
- **Following MACD to pick the side does not help**: short strike touched 15.5% of weeks
  following it, 14.6% doing the opposite (973 weeks).
- **Size is predictable.** Yesterday's VIX has a 0.64 rank correlation with today's range.
- **Calm score** = average 3-year percentile of 22-day return, MACD, distance from the 50-day
  average, RSI(14) and (inverted) share of downside volatility. All inputs known at the
  previous close; nothing fitted.

| Sample | Touched when calm >= 0.5 | Touched when calm < 0.5 |
|---|---|---|
| Nifty 2008-2012 | 21.5% | 36.0% |
| Nifty 2013-2017 | 19.3% | 35.1% |
| Nifty 2018-2022 | 19.4% | 35.1% |
| Nifty 2023-2026 | 25.8% | 32.5% |
| S&P 500 1990-2026 | 13.6% | 22.9% |
| Nasdaq 100 2001-2026 | 16.8% | 27.6% |

The gap held in every 5-year block of the S&P 500 from 1995. On Nifty it vanished in 2023
and 2024 (27.0% vs 27.7%, 32.3% vs 27.0%, average VIX 12.5 and 14.6) and returned in 2025-26.
A gradient-boosted model on 79 features did no better than this score (validation AUC 0.625
vs 0.636).

### Frozen rule, modelled prices

Iron condor, short strikes 0.10 delta, hedge about 0.8% of spot away, enter the first session
of the week only if calm >= 0.5, exit at the close if Nifty closes beyond a short strike,
otherwise the day before expiry. Sized so each trade's max loss is 4% of capital. Assumed
call IV 0.92 x VIX, put IV 1.12 x VIX; costs 2.5% of each leg price plus a fixed tick amount.

| Period | Trades | Return / yr | Max drawdown | Worst trade | Worst month | Worst year | Win rate |
|---|---|---|---|---|---|---|---|
| Train 2008-2016 | 215 | +4.6% | -9.4% | -5.1% | -8.3% | -4.4% | 82% |
| Validation 2017-2021 | 143 | +8.3% | -2.9% | -2.5% | -2.4% | +4.0% | 83% |
| **Holdout 2022-2026** | 106 | **+1.2%** | **-10.1%** | -4.1% | -5.0% | -0.4% | 77% |
| Same holdout, trading every week | 252 | +1.8% | -9.5% | -4.1% | -6.2% | -4.5% | 75% |

With call IV at 0.85 or 0.80 x VIX the holdout turns negative (-0.4% and -1.1% a year).

### Other results

- **Stops** (condor 0.10, flat-vol prices, 2008-2026): an intraday stop at 2x credit was hit in
  25% of trades and 41% of those would have ended in profit; a stop on a close beyond the short
  strike was hit in 12% and 9% would have ended in profit.
- **Entry day**: Monday was the weakest of five (-1.2% a year against +0.7% to +2.9%); the gaps
  are within noise. Shorter time to expiry looked better (research only; conflicts with the
  locked next-week-expiry rule).
- **Butterfly**: loss-to-win ratio 1.3 but only 56% winners; no better return.
- A regime exit and score-based sizing added nothing.

### Limits

- No real option prices: credits, skew and exit costs are assumptions.
- Daily data: no 10:00 entry, no intraday path; stops are approximated from the day's high/low.
- The holdout has been used once and is no longer unseen. The S&P and Nasdaq checks were run
  after seeing it.
- No event calendar, flows or open-interest data.

### What it means

Use the calm score as a skip / trade filter candidate, not as proof of profit. The next
evidence has to come from real option prices (the 2019-2026 bhavcopy through the engine) and
from forward paper trading, which is the only unseen data left.

---

## 2026-11-16 · Combination comparison on modelled prices (T4.8)

**Verdict: the symmetric iron condor at 0.12 delta with 200-300 point hedges was the best and
most consistent combination. Narrow 100-point hedges, call-heavy mixes and a 50% profit target
all made results worse. Returns stay small: +2.4% a year on the 2022-2026 period.**

Research only, **modelled option prices** (call IV 0.92 x VIX, put IV 1.12 x VIX), same data,
costs and calm gate (score >= 0.5) as the entry above. 18 combinations x management x profit
target x gate = 200 configurations, each sized to a max loss of 4% of capital. The 2022-2026
period had already been seen, so no period here is unseen. Code: `combos.py`.

| Combination (calm weeks, hold, close on a close beyond a short strike) | Train | Validation | 2022-26 | All years | Max drawdown | Worst month | Win rate | Avg loss / avg win |
|---|---|---|---|---|---|---|---|---|
| Condor 0.12, 300 wide | +6.1% | +9.7% | +2.4% | +6.0% | -10.2% | -8.7% | 80% | 2.1 |
| Condor 0.12, 200 wide | +5.5% | +9.3% | +2.0% | +5.6% | -10.7% | -8.7% | 80% | 2.2 |
| Call 0.08 + put 0.12, 200 wide | +4.6% | +9.1% | +2.0% | +5.1% | -10.6% | -7.4% | 82% | 2.6 |
| Condor 0.10, 300 wide | +5.0% | +8.4% | +1.5% | +5.0% | -9.4% | -8.3% | 84% | 2.7 |
| Condor 0.10, 200 wide | +4.6% | +8.3% | +1.2% | +4.7% | -10.0% | -8.3% | 82% | 2.5 |
| Put spread 0.10, 200 wide | +3.0% | +4.8% | +1.1% | +3.0% | -8.1% | -5.0% | 89% | 4.5 |
| Call 0.12 + put 0.08, 200 wide | +3.9% | +7.4% | +0.6% | +4.0% | -13.1% | -8.9% | 81% | 2.7 |
| Condor 0.08, 200 wide | +3.0% | +7.4% | +0.6% | +3.5% | -12.3% | -7.6% | 83% | 3.0 |
| Condor 0.10, 100 wide | +4.6% | +5.6% | -1.9% | +3.2% | -21.7% | -8.3% | 80% | 2.8 |
| Call spread 0.10, 200 wide | +1.3% | +2.9% | 0.0% | +1.4% | -9.3% | -9.0% | 86% | 4.6 |

Returns are % of capital per year. Median effect of each choice across the calm-week
configurations (all-years return, max drawdown):

- Hold to the time exit: +3.6%, -12.3%. Take profit at 50%: +1.5%, -14.2%.
- Two-sided position, close on a close beyond a short strike: +3.0%, -10.7%. No stop: +2.2%, -16.5%.
  Closing only the breached side gave the same result as closing everything.
- Calm gate on: +2.5%, -13.1%. Gate off: +0.4%, -31.6%.

Limits: as in the entry above. Costs are charged per leg, so narrow hedges (more lots for the
same max loss) pay more; that result depends on the assumed cost per leg.

---

## 2026-11-17 · Chart patterns on Nifty, daily / 4-hour / 1-hour (T4.8)

**Verdict: no pattern or pair of patterns predicted Nifty's direction reliably. The best pairs
won 60-70% of the time against a 50-57% baseline on 20-45 signals, and the share of pairs that
worked in both periods was what chance alone would produce.**

Research only. Index prices, no costs, no volume. Code: `research/2026-11-market-moves/patterns.py`.

| Item | Value |
|---|---|
| Data | Nifty daily 2007-09 to 2026-11 (train before 2017, test after); hourly 2023-12 to 2026-11 from Yahoo, split in half; 4-hour bars built as 09:15-13:15 and 13:15-15:30 |
| Patterns | High/low breakouts (20, 55, 250 bars), moving-average crosses, gaps, tight-range breakout, flag, support bounce / resistance rejection, head and shoulders, double top / bottom, triangle, engulfing, hammer / shooting star; rule-based definitions with swing points confirmed 3 bars late |
| Pairs | Each pattern with a trend state (price > 50 > 200 average, MACD above / below zero, above / below 200 average) or with another pattern in the last 3 bars |
| Trade | Signal at a bar's close, enter next open, exit at the close 5 or 10 bars later; repeat signals inside the hold dropped |

| Timeframe, hold | Single patterns better than baseline in both periods | Pairs better in both periods | Rank correlation of pair results, train vs test |
|---|---|---|---|
| Daily, 5 bars | 3 of 21 | 14 of 78 | 0.03 |
| Daily, 10 bars | 5 of 21 | 14 of 72 | 0.02 |
| 1-hour, 5 bars | 9 of 24 | 18 of 67 | -0.01 |
| 1-hour, 10 bars | 5 of 24 | 13 of 63 | -0.02 |
| 4-hour | 2 of 8 | too few signals | n/a |

Most consistent pairs (win rate against the baseline for the same side and period):

| Pair | Timeframe, hold | Train | Test |
|---|---|---|---|
| Price crosses above 50-bar average, in an uptrend | Daily, 5 | 68% vs 54% (n=31) | 61% vs 55% (n=44) |
| Price crosses above 50-bar average, in an uptrend | Daily, 10 | 61% vs 55% (n=28) | 71% vs 57% (n=38) |
| Bounce off support, in an uptrend | Daily, 5 | 58% vs 54% (n=19) | 79% vs 55% (n=19) |
| 20-bar high breakout, in an uptrend | 1-hour, 5 | 67% vs 51% (n=39) | 63% vs 50% (n=30) |
| 20-bar high breakout, MACD above zero | 1-hour, 5 | 63% vs 51% (n=52) | 57% vs 50% (n=42) |

Double tops and bottoms, triangles (long), hammers and gaps were below baseline. Head and
shoulders fired fewer than 8 times per period on every timeframe and could not be scored.
The 1-hour edges are 0.1-0.2% per trade before costs. With about 150 pairs tested and no
persistence between periods, the listed pairs are leads, not findings.

---

## 2026-11-18 · Monday open as the line: MACD + RSI direction, and an at-the-money hedged spread (T4.8)

**Verdict: MACD plus RSI does not tell which side of Monday's open Nifty will close on. Every
version was right 47-55% of the time, the same as a coin or as "always up". An at-the-money
spread with a 200-point hedge needs a 57-66% win rate to break even; the signals did not reach
it in both periods.**

Research only. Index prices; option credits are **modelled** (Black-Scholes, India VIX as
volatility, no skew), not traded prices. Code: `research/2026-11-market-moves/monday.py`.

| Item | Value |
|---|---|
| Data | Nifty daily 2007-09 to 2026-11-06, 986 weeks. Train before 2017, test from 2017 |
| Signal | MACD 12/26/9 and RSI 14 at the previous close; entry at the week's first open |
| Exit | Close of the same day, +1 day (this Tuesday), +4 (Friday), +6 (next Tuesday) |
| Spread | Sell at the money on the side the call says is safe, hedge 0.83% away (200 points at 24,000), hold to the expiry close, 3.5 points of costs |

Close on the called side of Monday's open, exit next Tuesday (+6), train / test:

| Call | Weeks | Right side | Right by 0.4%+ | Wrong by 0.4%+ |
|---|---|---|---|---|
| Always up (no signal) | 472 / 513 | 55% / 56% | 49% / 50% | 42% / 37% |
| MACD above its signal line | 472 / 513 | 52% / 50% | 48% / 43% | 43% / 45% |
| MACD above zero | 472 / 513 | 49% / 54% | 45% / 48% | 47% / 40% |
| RSI above 50 | 472 / 513 | 52% / 50% | 46% / 45% | 45% / 42% |
| MACD > signal and RSI > 50 (or both opposite) | 347 / 368 | 52% / 50% | 47% / 44% | 43% / 44% |
| MACD > signal, MACD > 0 and RSI > 50 (or all opposite) | 276 / 304 | 51% / 53% | 46% / 47% | 44% / 42% |
| Reversal: RSI < 35 up, RSI > 70 down | 80 / 85 | 45% / 47% | 39% / 44% | 49% / 46% |

Same-day and +1 day exits were 47-53% right for every call in both periods.

At-the-money spread, expiry next Tuesday, credit priced at 0.85 x VIX, train / test:

| Call | Win rate | Break-even win rate | Average per trade, % of money at risk | Worst run of losses, in full-loss units |
|---|---|---|---|---|
| Always sell the put side | 58% / 62% | 57% / 59% | +3.4 / +8.0 | 14 / 20 |
| Always sell the call side | 50% / 50% | 58% / 60% | -13.0 / -15.8 | 65 / 87 |
| MACD above its signal line | 57% / 55% | 58% / 60% | -0.1 / -5.3 | 20 / 38 |
| MACD > signal and RSI > 50 (or both opposite) | 57% / 56% | 58% / 60% | 0.0 / -3.7 | 14 / 29 |
| All three agree | 56% / 57% | 58% / 60% | -1.3 / -1.0 | 14 / 17 |

Expiry the next day (+1): win rates 53-58% in training against 61-63% needed (all negative),
and 59-66% in the test period against 64-66% needed (about zero). The only positive line in both
periods is "always sell the put side" for the longer expiry, which is the market's upward drift,
not the signal; its worst single trade is a full loss and its worst run was 14-20 full losses.
The modelled credit ignores skew and real bid/ask, so real results would be lower.

---

## 2026-11-18 · "Win big, lose small" on Nifty: fixed stop with a larger target or trailing stop (T4.8)

**Verdict: the wins can be made larger than the losses (1.4 to 2.4 times), but the win rate then
falls to 30-46%, never 50-60%. The two cancel: the best rules made 2-5 R a year (about 2-5% a
year at 1% risk per trade) with drawdowns of 9-28 R. No rule came near 20-30% a year.**

Research only. Index prices as a stand-in for the future, 0.05% cost per trade, stop assumed
first when stop and target share a day. Code: `research/2026-11-market-moves/skew.py`.
Nifty daily 2007-09 to 2026-11-06, train before 2017, test from 2017. R = amount risked per trade.

| Entry, exit | Win rate (train / test) | Win size / loss size | R per year | Max drawdown, R |
|---|---|---|---|---|
| MACD above zero, long only; stop 1.5 ATR, trail 2.5 ATR | 34% / 41% | 2.3 / 2.1 | 1.9 / 4.4 | -10.9 / -8.9 |
| MACD above zero, long only; stop 1 ATR, target 3 ATR | 32% / 36% | 2.4 / 2.4 | 2.0 / 5.5 | -14.8 / -12.0 |
| Breakout up in an uptrend; stop 1.5 ATR, trail 2.5 ATR | 44% / 45% | 1.9 / 1.9 | 1.3 / 1.9 | -4.1 / -10.6 |
| MACD and RSI agree; stop 1 ATR, target 2 ATR | 38% / 37% | 1.8 / 1.8 | 3.3 / 1.4 | -15.6 / -21.0 |
| Always long; stop 1.5 ATR, trail 2.5 ATR | 34% / 36% | 2.2 / 2.2 | 2.4 / 4.1 | -14.0 / -17.5 |
| 20-day breakout, long and short; stop 1 ATR, target 2 ATR | 37% / 34% | 1.8 / 1.8 | 1.0 / -1.1 | -15.6 / -35.9 |

17 of 32 entry/exit pairs were positive in both periods, all with an average of 0.0-0.25 R per
trade. Raising risk per trade to reach 20% a year would scale the drawdown the same way (4-10
times), past the 5% yearly limit in `AGENTS.md`.

---

## 2026-11-20 · Wednesday to next Tuesday, direction from the MACD histogram's slope (T4.8)

**Verdict: 20 wins in 40 weeks of 2026 (50%), average win +1.39% and average loss -1.39%,
net zero. Over 2008-2026 it won 444 of 895 (50%).**

Research only, index prices, no costs. Code: `research/2026-11-market-moves/wed_macd.py`.
Rule: histogram (12/26/9, daily) falling at Tuesday's close (green shrinking or red growing)
calls "below"; rising (red shrinking or green growing) calls "above". Entry Wednesday open,
exit next Tuesday close. Data to 2026-11-03.

| 2026 | Wins | Average result |
|---|---|---|
| All calls | 20 of 40 (50%) | 0.00% |
| Call "below" | 12 of 22 (55%) | +0.18% |
| Call "above" | 8 of 18 (44%) | -0.23% |
| Green shrinking | 6 of 9 | +0.25% |
| Red growing | 6 of 13 | +0.14% |
| Red shrinking | 6 of 10 | -0.04% |
| Green growing | 2 of 8 | -0.46% |

By year the rule won 44-54% in every year except 2020 (63%). 2026 was a falling year (Nifty
closed above the Wednesday entry in only 45% of weeks), which is why "below" calls did better.

---

## 2026-11-20 · 9 / 21 EMA crossover on Nifty daily: when it worked and when not (T4.8)

**Verdict: the crossover wins only about 35% of the time and lives on a few large trends: the
best 18 of 185 trades made more than the whole profit. Buy crosses were positive in both
periods; sell crosses lost in both. No condition made it reliable in the sense of winning most
of the time.**

Research only, index prices, 0.05% cost per trade. Code: `research/2026-11-market-moves/ema_cross.py`.
Nifty daily 2008-07 to 2026-11-06, 185 crossovers (about 10 a year, median hold 19 days). Signal
at the cross close, entry next open, exit at the opposite cross. Train before 2017 / test from 2017.

| Condition at the cross | Win rate | Average per trade |
|---|---|---|
| Every crossover | 34% / 35% | +0.48% / +0.71% |
| Buy cross | 39% / 47% | +1.45% / +1.96% |
| Sell cross | 30% / 23% | -0.49% / -0.56% |
| In the direction of the 200-day trend | 43% / 40% | +1.21% / +0.99% |
| Against the 200-day trend | 25% / 31% | -0.26% / +0.44% |
| Sell cross while price is above the 200-day average | 24% / 25% | -1.39% / -0.30% |
| MACD already on the same side of zero | 43% / 41% | +0.81% / +0.68% |
| Cross made by one bar larger than 1 ATR | 36% / 21% | -0.46% / -0.82% |
| Cross made by a normal bar | 33% / 41% | +0.79% / +1.36% |
| VIX 20 or more | 28% / 24% | +0.74% / +0.55% |

Average win +6.05%, average loss -2.28%, best +51.1%, worst -8.1%. ADX level, the slope of the
21 EMA and the time since the previous cross gave results that flipped between periods.
2026 had 12 crossovers; 3 of the 11 closed ones made money.
With about 30 condition groups tested on 40-100 trades each, only differences that hold in both
periods (buy vs sell, with vs against trend, large cross bar) should be given any weight.

---

## 2026-11-20 · MACD as a range filter, Wednesday to next Tuesday (T4.8)

**Verdict: MACD does not give direction, but it does say something about range. With MACD above
zero Nifty touched a level 3% below entry in 21% / 10% of weeks (train / test) against 32% / 20%
with MACD below zero. Part of that is just VIX: once the level is placed by VIX, MACD still
lowers the downside touch rate (23% / 20% against 27% / 34%) but adds nothing on the upside.**

Research only, index prices, no option prices. Code: `research/2026-11-market-moves/macd_range.py`.
886 weeks, 2008-03 to 2026-10, entry Wednesday open, exit next Tuesday close, state at Tuesday's
close. "Touched" = traded there at any time in the week. Train before 2017 / test from 2017.

| State | Touched 2% below | Touched 2% above | Touched 3% below | Touched 3% above |
|---|---|---|---|---|
| Every week | 38% / 26% | 39% / 26% | 26% / 13% | 22% / 8% |
| MACD above zero | 34% / 21% | 36% / 23% | 21% / 10% | 19% / 6% |
| MACD below zero | 44% / 36% | 43% / 31% | 32% / 20% | 27% / 13% |
| MACD above zero, bars rising | 29% / 19% | 33% / 20% | 20% / 7% | 22% / 2% |
| MACD above zero and VIX under 16 | 22% / 15% | 22% / 17% | 7% / 4% | 7% / 2% |
| MACD below zero and VIX 20+ | 51% / 47% | 54% / 58% | 42% / 37% | 39% / 26% |
| VIX 20+ (any MACD) | 45% / 43% | 53% / 50% | 35% / 33% | 36% / 26% |

Level placed one VIX-implied weekly move away (VIX / sqrt(52)):

| State | Touched below | Touched above |
|---|---|---|
| Every week | 25% / 25% | 21% / 20% |
| MACD above zero | 23% / 20% | 19% / 20% |
| MACD below zero | 27% / 34% | 25% / 21% |
| MACD above zero, bars rising | 20% / 18% | 21% / 16% |
| MACD below zero, bars falling | 30% / 38% | 30% / 17% |

Option premiums are priced from VIX, so the tradable part of this is only the last table: a
few points lower touch rate on the put side when MACD is above zero. Whether that pays after
real premiums and costs is not tested here.

---

## 2026-11-20 · Weekly range model, built on 2016-2020, tested once on 2021-2026 (T4.8)

**Verdict: the rule chosen on 2016-2020 was profitable in all six test years, but small:
+0.65 R a year (R = the maximum loss of one trade), worst trade -0.26 R, max drawdown -0.55 R.
At the 1% weekly loss limit that is about 0.65% a year, not 20%. The machine-learning model did
not beat a plain VIX multiple.**

Research only. Option prices are **modelled** (Black-Scholes, India VIX, assumed skew), not
quotes. Code: `research/2026-11-market-moves/rangeml.py`.

| Item | Value |
|---|---|
| Framing (owner's) | Predict a limit X the week will not cross; sell a strike 1.5% beyond X; exit if price reaches X |
| Build data | 2016-2020: 1,228 daily samples, 28 features known before the open (VIX, realised volatility, MACD, RSI, trend distance, US markets, rupee, oil) |
| Models | LightGBM quantile regression (80th and 90th percentile of the week's largest move up and down) against VIX x 0.8 / 1.0 / 1.25 / 1.5 |
| Rule choice | Walk-forward inside the build years (fit 2016-18, predict 2019; fit 2016-19, predict 2020); 72 rules scored on return less drawdown |
| Trade | Week's first open, spread with hedge about 0.8% further, short delta capped at 0.12, exit at the close the day before expiry, costs included |
| Frozen rule | X = 0.8 x VIX-implied move, both sides, only when MACD is above zero |
| Test | 2021-01-04 to 2026-10-26, 304 weeks, run once |

Did the limit hold on the test years (share of weeks price stayed inside X on both sides)?

| Limit | Average X | Up side held | Down side held | Both held |
|---|---|---|---|---|
| Model, 80th percentile | 2.4% / 2.8% | 76% | 81% | 58% |
| Model, 90th percentile | 3.0% / 3.7% | 85% | 88% | 73% |
| VIX x 1.0 | 2.4% | 78% | 76% | 55% |
| VIX x 1.25 | 3.0% | 88% | 85% | 73% |
| VIX x 1.5 | 3.5% | 93% | 89% | 83% |

Test result:

| Rule | Trades | Weeks inside X | Winning trades | R per year | Max drawdown | Worst trade | Up years |
|---|---|---|---|---|---|---|---|
| **Frozen: VIX x 0.8, both sides, MACD > 0** | 188 | 38% | 61% | **+0.65** | -0.55 | -0.26 | 6 of 6 |
| Same without the MACD filter | 304 | 33% | 54% | -0.24 | -3.59 | -1.05 | 3 of 6 |
| VIX x 1.0, both sides, MACD > 0 and VIX < 20 | 170 | 60% | 65% | +0.47 | -0.86 | -0.27 | 5 of 6 |
| VIX x 1.25, put side, MACD > 0 and VIX < 20 | 170 | 89% | 89% | +0.19 | -1.45 | -1.07 | 4 of 6 |
| Model 90th percentile, both sides, MACD > 0 and VIX < 20 | 169 | 77% | 80% | +0.15 | -1.53 | -1.04 | 5 of 6 |

Frozen rule by year (R): 2021 +0.30, 2022 +0.64, 2023 +0.49, 2024 +0.85, 2025 +0.92, 2026 +0.59.
Average winning trade +0.10 R, average losing trade -0.10 R. All 72 rules on the test years:
best +0.65, median +0.06, worst -0.58 R a year; the frozen rule happened to be the best, so
expect less in future. A wider limit wins more often (89%) but earns less and keeps the
full-loss trade. Reaching 20% a year with the frozen rule would need about 30 times the size,
a possible loss of about 30% of capital on one trade.

---

## 2026-11-20 · Search of 83,880 rule combinations for 20% a year inside the loss limits (T4.8)

**Verdict: no combination can make 20% a year inside the loss limits, even on the years it was
searched on. The best of 57,330 rules made 2.8 R a year in 2016-2020; 20% with a 3% cap on one
position's loss needs 6.7 R. One family of rules did hold up on both unseen periods, with 92-100%
winning trades, but it earns 0.4-0.6 R a year: 20% from it means risking about half the capital
on a single trade.**

Research only. Option prices are **modelled** (Black-Scholes, India VIX, assumed skew), not
quotes. Code: `research/2026-11-market-moves/searchcombo.py`.

| Item | Value |
|---|---|
| Set-ups (180) | Entry on the week's first day or Wednesday; put side, call side or both; limit X = 0.6 to 1.5 x VIX-implied move; strike 1.5% or 0.5% beyond X; exit at X, on a close beyond the strike, or hold; short delta capped at 0.12; exit the day before expiry |
| Filters (466) | None, one, or any two of 30 conditions: VIX ranges, MACD sign and bar direction, RSI ranges, 50 / 200-day trend, realised volatility against VIX, VIX direction, last week's direction, US VIX |
| Search period | 2016-2020 only; rules must trade at least 10 times a year (57,330 rules) |
| Unseen checks | 2021-2026 and 2011-2015 |
| Test "could make 20%" | A: return / drawdown >= 4 (20% with drawdown within 5%). B: return / worst trade >= 20 (worst trade within 1%). C: R per year >= 6.67 (one position's max loss within 3%) |

| Stage | Rules |
|---|---|
| Positive in 2016-2020 | 49,918 |
| Pass A in 2016-2020 | 951 |
| Pass A and B in 2016-2020 | 209 |
| Pass A, B and C in 2016-2020 | **0** |
| Of the 951: still positive in 2021-2026 | 663 |
| Of the 951: pass A in 2021-2026 | 25 |
| Of the 951: pass A in 2011-2015 | 31 |
| Of the 951: pass A in both unseen periods | **5 (one family)** |

Median of the 951: 0.41 R a year in the search years, 0.08 in 2021-2026, 0.11 in 2011-2015.

The surviving family: enter Wednesday, only when MACD bars are rising and RSI is above 60,
strikes far out, hold to the day before expiry (about 10 trades a year).

| Variant | 2016-2020 | 2021-2026 | 2011-2015 |
|---|---|---|---|
| Both sides, X = 1.25 x VIX, strike 1.5% beyond | 57 trades, 100% won, +0.61 R/yr | 50 trades, 92% won, +0.38 R/yr, worst -0.08 R, 6 of 6 years up | +0.42 R/yr, worst -0.09 R |
| Both sides, X = 1.5 x VIX | 100% won, +0.34 R/yr | 96% won, +0.22 R/yr, worst -0.04 R | +0.26 R/yr |
| Put side, X = 1.5 x VIX | 100% won, +0.24 R/yr | 96% won, +0.16 R/yr, worst -0.01 R | +0.18 R/yr |

Size and what it means for the first variant (weakest period, +0.38 R a year):

| Max loss of one trade, % of capital | Return a year | Worst trade seen | If the trade ever loses fully |
|---|---|---|---|
| 1% (weekly limit) | 0.4% | -0.1% | -1% |
| 3% (monthly limit) | 1.1% | -0.3% | -3% |
| 11% | 4.2% | -1.0% | -11% |
| 52% | 20% | -4.7% | -52% |

No full loss occurred in about 160 trades over 16 years, which does not mean it cannot. Five
survivors out of 951 is more than chance would give (about 0.6% of all rules pass A in an unseen
period), but they are variants of one rule and were found by testing 57,330.

---

## 2026-11-20 · Free sizing: which rule reaches 8-20% a year, and at what risk (T4.8)

**Verdict: with no loss cap, the rules that looked safest for ten years (up 10 of 10 years,
worst trade -0.15 R) were the ones that broke: sized for 8-20% they made 3-7% in 2021-2026 with
one week of -13% to -37%. The one rule that held on all three periods is the earlier frozen
one, which exits when price reaches the limit. Sized on 2016-2020 for 8 / 12 / 20% it made
6.4 / 9.5 / 15.7% a year in 2021-2026 and 2.8 / 4.1 / 6.4% in 2011-2015.**

Research only. Option prices are **modelled** (Black-Scholes, India VIX, assumed skew), not
quotes. Code: `research/2026-11-market-moves/searchsize.py`. Correction to the previous entry:
its Wednesday set-ups assumed 7 sessions to expiry; this run uses the real calendar (entry
Monday, Tuesday or Wednesday, expiry the next week's Tuesday, exit the session before). The
"Wednesday, MACD bars rising and RSI above 60" family from that entry should be disregarded.

Kept: hedged spreads, short delta at most 0.12, next week's expiry, exit before expiry day.
Dropped for this study: weekly, monthly and yearly loss limits (owner's instruction).
125,820 rules; chosen on 2011-2020 (positive in both halves, up in 9+ of 10 years, no trade
worse than -0.6 R: 7,352 rules); 2021-2026 used only to check.

Top three chosen rules, size set on 2011-2020, then applied to 2021-2026:

| Rule (all hold to the day before expiry) | Target | One full loss costs | 2011-2020: CAGR, max drawdown | 2021-2026: CAGR, max drawdown, worst week |
|---|---|---|---|---|
| Tuesday, put side, 1.25 x VIX, MACD bars falling and realised vol under 0.8 x VIX | 8% | 16.5% | 8.0%, -2.4% | 3.1%, -15.5%, -15.5% |
| same | 20% | 39.5% | 20.0%, -5.8% | 6.4%, -37.0%, -37.0% |
| Monday, both sides, 1.25 x VIX, MACD bars falling and last 5 days up | 8% | 17.4% | 8.0%, -1.3% | -2.7%, -25.0%, -14.6% |
| same | 20% | 41.7% | 20.0%, -3.2% | -8.0%, -54.9%, -34.8% |
| Tuesday, put side, 1.5 x VIX, realised vol under 0.8 x VIX | 8% | 16.6% | 8.0%, -2.3% | 3.3%, -13.4%, -13.4% |
| same | 20% | 39.4% | 20.0%, -5.5% | 7.3%, -31.9%, -31.9% |

All 7,352 chosen rules in 2021-2026: 84% positive, median +0.15 R a year against +0.33 in
2011-2020. Rules that hold or exit only on a close beyond the strike had a median worst trade
of -0.81 R in 2021-2026.

The earlier frozen rule (Monday, both sides, limit 0.8 x VIX move, strike 1.5% beyond, exit
when price reaches the limit, only when MACD is above zero; about 32 trades a year):

| Period | Trades | Won | R per year | Max drawdown | Worst trade | Up years |
|---|---|---|---|---|---|---|
| 2011-2015 (never used to choose it) | 140 | 52% | +0.35 | -1.01 | -0.33 | 3 of 5 |
| 2016-2020 (chosen here) | 170 | 59% | +0.95 | -0.79 | -0.32 | 5 of 5 |
| 2021-2026 (test) | 179 | 62% | +0.76 | -0.52 | -0.30 | 6 of 6 |

Sized on 2016-2020:

| Target | One full loss costs | 2021-2026: CAGR, max drawdown, worst week, worst year | 2011-2015: CAGR, max drawdown, worst year |
|---|---|---|---|
| 8% | 8.3% | 6.4%, -4.3%, -2.5%, +3.2% | 2.8%, -8.1%, -5.0% |
| 10% | 10.3% | 7.9%, -5.3%, -3.1%, +3.9% | 3.5%, -10.0%, -6.3% |
| 12% | 12.3% | 9.5%, -6.3%, -3.7%, +4.6% | 4.1%, -11.9%, -7.5% |
| 15% | 15.3% | 11.8%, -7.8%, -4.5%, +5.6% | 5.0%, -14.6%, -9.3% |
| 20% | 20.1% | 15.7%, -10.3%, -6.0%, +7.1% | 6.4%, -18.9%, -12.2% |

Its worst trade was about -0.3 R in every period because the exit comes before the strike. The
same set-up under other filters (VIX under 20, above the 200-day average) had trades of -1.0 R:
a gap through the limit and the strike is possible and would cost the "one full loss" column.
The exit at the limit is assumed to fill at the modelled price; real fills are untested.
These sizes break the loss limits in `AGENTS.md` section 1, which only the owner can change.

---

## 2026-11-20 · The frozen rule by entry day (T4.8)

**Verdict: Tuesday entry (for the next week's Tuesday expiry) was the best day in each of the
three periods; Friday was the weakest. The MACD filter roughly halved the drawdown on every day.**

Research only, modelled option prices. Code: `research/2026-11-market-moves/entry_day.py`.
Set-up unchanged: both sides, limit 0.8 x VIX move, strike 1.5% beyond, exit when price reaches
the limit, only when MACD is above zero. R per year / max drawdown / worst trade:

| Entry day | 2011-2015 | 2016-2020 | 2021-2026 |
|---|---|---|---|
| Monday | +0.35 / -1.01 / -0.33 | +0.95 / -0.79 / -0.32 | +0.76 / -0.52 / -0.30 |
| Tuesday | +0.75 / -0.71 / -0.35 | +1.63 / -0.90 / -0.54 | +1.08 / -0.84 / -0.29 |
| Wednesday | +0.46 / -0.69 / -0.25 | +1.10 / -0.92 / -0.54 | +0.52 / -0.51 / -0.30 |
| Thursday (under 6 days to expiry) | +0.21 / -0.74 / -0.30 | +1.18 / -0.71 / -0.51 | +0.32 / -0.58 / -0.30 |
| Friday (under 6 days to expiry) | +0.22 / -0.98 / -0.44 | +0.76 / -0.30 / -0.30 | +0.16 / -0.85 / -0.40 |

Without the MACD filter the Monday drawdown was -1.98 / -1.72 / -2.32 and the worst trade
reached -1.05. The day was compared after seeing all three periods, so the Tuesday advantage
is a lead to confirm on real prices, not a tested result. Speed note: one simulated trade is
about 6 daily bars and a few Black-Scholes evaluations (about 0.05 ms); the 125,820-rule search
simulated 270 set-ups x about 800 entry days once, then applied filters as yes/no masks.
