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
