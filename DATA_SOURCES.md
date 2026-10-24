# Historical Data Sources (T1.1)

Research date: 2026-10-24. Prices and limits change, so verify before buying.

## What the backtest needs

| Need | Why |
|---|---|
| **All strikes** out to ~1,000+ pts from spot, for next week's expiry | Our short strikes are 0.08–0.12 delta (~500–800 pts OTM) and hedges are 100–200 pts further |
| Back to **Feb 2019** (Nifty weekly options start) | Enough years and regimes (2020 crash, 2022 bear, 2024 election) |
| Intraday (1-min or 5-min) | 10:00 entries, 1-min stop checks |
| Bid / ask, or a way to model it | `AGENTS.md` §5: no mid-price fills |
| OI, volume | Liquidity filter, features |
| Spot, futures, India VIX | Forward, features |

Rough strike distance: Nifty ~25,000, IV ~13%, 8 days → 1 standard deviation ≈ 480 pts,
so 0.10 delta ≈ 600+ pts OTM. Hedges sit at ~800 pts or more.

## Options compared

| Source | Strikes | History | Granularity | Bid/ask | Cost | Fit |
|---|---|---|---|---|---|---|
| **Dhan Expired Options API** (`/charts/rollingoption`) | **Rolling ATM ±10 strikes at most** (index options near expiry), ATM ±3 otherwise. ±10 × 50 = ±500 pts | 5 years | 1 / 5 / 15 / 25 / 60 min; OHLC, volume, OI, IV, spot | No | Included with Dhan Data API | ❌ **Can't reach our strikes or hedges.** Useful only for ATM IV / term structure features |
| **NSE F&O bhavcopy** (official daily file) | **All strikes, all expiries** | Many years (covers all of 2019+) | **Daily**: open, high, low, close, settle, OI, volume per contract | No | **Free** | ✅ **Best first step.** Full chain, official, free. No intraday, no bid/ask |
| **NSE-authorized vendors** (TrueData, Global Datafeeds, Accelpix) | Full chain | Typically 2016+ for index options | 1-min bars (tick / 1-sec snapshots at higher cost) | Usually no historical bid/ask in bar data (ask) | Forum reports: ~₹4K/yr (2022) to ₹15–20K/yr for tick; **get current quotes** | ✅ **Second step**, only if the daily backtest passes |
| AngelOne / Zerodha historical APIs | Active contracts; expired options limited or not available | Limited | Intraday | No | Free with account | ❌ Not for expired options history |
| Our own live recording (Dhan WebSocket, from now on) | Full chain we subscribe to | Starts today | Tick / 1-min, **with bid / ask** | **Yes** | Included | ✅ **Start early.** The only source of real bid/ask; calibrates the spread model |

Notes:
- NSE moved the F&O bhavcopy to a new file format (UDiFF) in 2024, so the downloader must
  read both the old and new formats (verify the exact switch date in T1.3).
- NSE's site blocks plain scripted requests; the downloader needs proper headers,
  sessions, retry with limits, and polite rate limiting.
- Historical vendor data is usually 1-min bars from exchange snapshots, not true ticks.

## Recommendation: three steps

### Step 1: daily backtest on NSE bhavcopy (free, start now)

- Full chain, every expiry, 2019 → today.
- Entry at the day's price (conservative: buy at high, sell at low as a worst case, or
  close ± a modeled spread).
- Stops checked on the daily high / low of each leg, with gaps assumed against us.
  Conservative by design: if it passes the go / no-go bar like this, intraday reality is
  unlikely to be worse.
- **Answers the key question for ₹0: is there an edge at all?**

### Step 2: buy 1-min full-chain data (only if Step 1 passes)

- Get quotes from TrueData, Global Datafeeds and Accelpix for Nifty weekly options,
  1-min, Feb 2019 → today, all strikes.
- Use it to test 10:00 entries, 1-min stops, intraday exits.

### Step 3: record live data from Dhan now

- Start the live recorder (feed gateway, T5.3) early, even before the strategy is ready.
- Every week of recorded data gives real bid / ask spreads at our strikes, which makes the
  backtest's spread model honest.

### Dhan expired options API: limited use

- ATM IV, ATM straddle price, IV term structure as features. Not for pricing our trades.

## Accelpix: which plan?

Their public plans (Pix Connect: Smart ₹1,599, Elite ₹2,099, Pro ₹2,499, Ultimate ₹3,499
per month + GST) are **live charting subscriptions**. They keep only 45–120 days of 1-min
history, and the pages don't say whether expired options are covered. **None of these
plans gives us 2019 → today of expired weekly options.**

What to buy instead: a **one-time historical data purchase** (a forum user reports buying
expired options history from Accelpix). Ask sales for a quote with this spec:

> Nifty 50 weekly + monthly options, **all strikes, all expiries, expired contracts
> included**, Feb 2019 → today, **1-minute OHLC + volume + OI**, plus Nifty spot, Nifty
> futures and India VIX 1-min for the same period. CSV or Parquet. Please confirm: strike
> coverage (any limit by moneyness?), missing-day handling, whether bid/ask is available,
> licence for personal research use, price, and an ongoing update option.

Get the same quote from TrueData and Global Datafeeds, then compare on coverage of a few
sample days (we check them against the NSE bhavcopy close prices).

Later, for live data, **Dhan** stays the feed. An Accelpix live plan is only useful as a
backup feed (Pro / Ultimate, because only those include options OI).

## Proposed task changes

- T1.3 / T1.4 / T1.5 target **NSE bhavcopy** first.
- Move a minimal **live recorder** (T5.2 + T5.3, record-only) up to run right after M1.
- Add vendor quote requests (owner) before Step 2.

## Sources

- Dhan Expired Options Data API docs: https://dhanhq.co/docs/v2/expired-options-data/
- Dhan FAQ, expired options via API: https://dhan.co/support/platforms/dhanhq-api/do-dhan-provides-expired-options-data-via-the-api-s/
- Dhan FAQ, fixed strike with rolling API: https://dhan.co/support/platforms/dhanhq-api/can-i-fetch-ohlc-data-for-a-fixed-option-strike-throughout-the-entire-trading-session-using-the-rolling-option-data-api/
- `nser` package (NSE F&O bhavcopy downloads): https://archive.linux.duke.edu/cran/web/packages/nser/vignettes/fobhav.html
- Vendor pricing discussion: https://tradingqna.com/t/received-quote-for-historical-bank-nifty-1-min-data/135259
- Vendor data quality: https://www.marketcalls.in/softwares/data-vendors-and-quality-of-datafeeds.html
- TrueData market data API: https://www.truedata.in/products/marketdataapi
