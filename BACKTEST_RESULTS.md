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
