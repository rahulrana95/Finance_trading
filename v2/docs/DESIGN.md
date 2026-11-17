# v2 Design

**Status: DRAFT, waiting for owner approval.** Date: 2026-11-17.
All thresholds below are settings with the stated defaults. They come from the research in
`research/2026-11-market-moves/`; none is a guarantee.

## 1. Definitions

| Term | Definition |
|---|---|
| Reference high | Highest daily close of the last 126 trading days, including today |
| Below high | `1 - last_price / reference_high`, as a percentage |
| Fall event (X%) | First day the close is at least X% below the reference high; it ends when a close is back at that reference high |
| Recovery time | Trading days from the fall event to its end |
| Buy levels | 10%, 20%, 30% below the cycle's reference high |
| Cycle | Starts at the first buy level; its reference high is frozen until the cycle ends |
| Target | The cycle's frozen reference high: sell everything bought in the cycle |
| Hard exit | 40% below the frozen reference high: close the cycle and stop adding |

## 2. Data model (Postgres)

All tables have `id`, `created_at`. Money is `numeric`, never float. Logs are append-only.

| Table | Key columns |
|---|---|
| `stocks` | `symbol` (unique), `name`, `industry`, `status` (approved, watching, rejected), `in_fno`, `lot_size`, `notes` |
| `daily_prices` | `symbol`, `date`, `open`, `high`, `low`, `close`, `volume`, `source`, unique (`symbol`, `date`) |
| `latest_prices` | `symbol`, `price`, `as_of`, `source` |
| `financials` | `symbol`, `period` (FY2026, Q2FY27), `revenue`, `net_profit`, `total_debt`, `equity`, `promoter_holding_pct`, `promoter_pledge_pct`, `source`, `entered_by`, unique (`symbol`, `period`) |
| `stock_metrics` | `symbol`, `as_of`, `reference_high`, `below_high_pct`, `history_years`, `falls_10`, `recovered_12m_pct`, `longest_recovery_days`, `open_fall_days`, `max_drawdown_pct`, `stability_score`, `financial_score`, `evidence_score`, `needs` (list) |
| `settings` | one row: paper capital, per-stock cap, levels, parts, limits, kill switch, default mode |
| `runs` | `kind` (scheduled, on_demand, dry_run, screener), `started_at`, `finished_at`, `status`, `summary` |
| `run_steps` | `run_id`, `seq`, `at`, `subject`, `level` (ok, info, action, warn, error), `message` |
| `recommendations` | `run_id`, `symbol`, `kind` (entry, exit), `zone`, `step`, `instrument_type` (cash, future, combo), `plan` (JSON), `evidence_score`, `reasons` (JSON), `risk` (JSON), `status` (new, approved, skipped, expired), `valid_until` |
| `orders` | `recommendation_id`, `mode` (paper, real), `symbol`, `instrument` (cash, future), `side`, `quantity`, `limit_price`, `status` (open, filled, rejected, cancelled), `reason` |
| `fills` | `order_id`, `mode`, `price`, `quantity`, `charges`, `price_source`, `filled_at` |
| `cycles` | `symbol`, `mode`, `reference_high`, `opened_at`, `closed_at`, `close_reason` (target, hard_exit, manual) |
| `positions` (view) | Built from fills: per `symbol`, `instrument`, `mode`, `cycle_id` |

## 3. Core logic

### 3.1 Metrics (`core/metrics.py`)

- `reference_high(closes, window=126)`; needs at least 60 closes, else "needs data".
- `fall_events(closes, pct)` returns each event with start, depth, recovery days or open days.
- `recovery_stats(events)`: count, share recovered within 252 days, longest recovery, longest
  open fall.
- `max_drawdown(closes)`, `annual_volatility(closes)`, `history_years(dates)`.

### 3.2 Stability score, 0 to 100 (`core/scoring.py`)

| Part | Full marks when | Weight |
|---|---|---|
| Quick recovery | 90% or more of 10% falls back within 12 months (linear from 50%) | 35 |
| No long fall | Longest recovery 252 days or less (linear to 0 at 756) | 20 |
| Nothing open | No unrecovered fall older than 126 days | 15 |
| Shallow worst fall | Max drawdown 30% or less (linear to 0 at 70%) | 15 |
| Enough history | 8 years or more of prices (linear from 3) | 15 |

Fewer than 5 fall events: the recovery parts are capped at half marks and `needs` gets
"few past falls to judge".

### 3.3 Financial check, 0 to 100 (`core/financials.py`)

| Check | Pass | Weight |
|---|---|---|
| Revenue growing | Latest year above the year 4 years earlier | 20 |
| Profit every year | Net profit positive in each of the last 5 years | 25 |
| Profit growing | Latest year above the year 4 years earlier | 20 |
| Debt modest | Debt to equity below 1.0; skipped for banks and lenders | 20 |
| No pledge | Promoter pledge is 0% | 15 |

A check with missing inputs scores 0 and adds a line to `needs`, for example
"net profit for FY2022 and FY2023". Banks get the debt weight redistributed.

### 3.4 Evidence score and "needs data"

`evidence_score = 0.5 * stability + 0.3 * financial + 0.2 * data_quality`, where
`data_quality` is 100 minus 20 for each of: price older than 1 trading day, fewer than 8
years of history, financials older than 15 months, any missing financial field, public
(unofficial) price source. It is an index of how much evidence supports the stock. It is
not a probability and the interface never shows it with a percent-chance wording.

### 3.5 Zones (`core/zones.py`)

`zone(below_high_pct, levels)` returns 0 (not in a buy zone) or the deepest level reached
(1, 2, 3). `next_level_price(reference_high, level)`.

### 3.6 Plan and instrument choice (`core/plan.py`)

- Per-stock allocation = `min(per_stock_cap * capital, capital / approved_count)`.
- Step amounts = allocation × parts / sum(parts); with parts 1 : 2 : 3 that is 1/6, 2/6, 3/6.
- A step is offered only when its level has been reached and it has not been filled in the
  current cycle. A deeper level reached first offers all untaken steps up to it.
- Instrument per step:
  - **Cash** (shares): quantity = floor(step amount / price); if that is 0 the step is
    skipped with the reason "step smaller than one share".
  - **Futures** allowed for a step only if all hold: the step index is at or beyond
    `futures_from_step` (default 3), the stock is in futures with a known lot size, one
    lot's value is at most the step amount, and margin cover after the trade stays at or
    above the floor (default 2×). Otherwise the step falls back to cash.
- `instrument_type` of the recommendation: `cash` if no step uses futures, `future` if every
  offered step does, `combo` otherwise.

### 3.7 Risk check (`core/risk.py`)

Rejects with a reason when any of these is true: kill switch on; stock not approved; prices
stale; drawdown from peak capital at or beyond the pause limit; position value for the
stock would exceed the per-stock cap; total exposure would exceed the cap; margin cover
below the floor; a real order while real mode is locked; the cycle is past its hard exit.

### 3.8 Paper fills and charges

- An open paper order fills at the next latest price that is newer than the order and no
  worse than its limit; buys pay 0.05% slippage, sells receive 0.05% less.
- Charges per fill from `core/charges.py`: brokerage, STT, exchange fee, GST, stamp duty,
  with separate tables for delivery shares and futures.
- No fill on a stale price or outside market hours.

### 3.9 Profit or loss (`core/pnl.py`)

Average-cost positions per symbol, instrument, mode and cycle. Realised = sum over closed
quantity of (sell − average cost) minus charges. Unrealised = (last price − average cost) ×
open quantity. Futures also accrue a holding cost shown separately.

## 4. Services

| Service | Steps |
|---|---|
| `screener.run()` | For each stock: fetch missing daily prices, compute metrics and scores, write `stock_metrics`, log changes. One stock failing does not stop the rest. |
| `algo_run.run(kind)` | Pre-checks, per-stock zone and plan, risk check, write recommendations and run steps. `dry_run` writes steps only. |
| `trading.approve(rec_id, mode)` | Re-check risk at current price, create the order, then for paper ask the paper broker to fill. |
| `trading.skip(rec_id, note)` | Mark skipped and store the note for later learning. |
| `portfolio.open_trades(mode)` / `portfolio.summary(mode)` | Build views from fills and latest prices. |

## 5. API

All routes need a valid session except `/api/health`.

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Liveness |
| `GET /api/me` | Current user |
| `GET /api/stocks?status=&zone=&min_score=&sort=` | Stock table with metrics and needs |
| `GET /api/stocks/{symbol}` | Detail: levels, falls history, financials, needs |
| `PATCH /api/stocks/{symbol}` | Change status or notes |
| `POST /api/stocks/{symbol}/financials` | Add or replace a period's figures |
| `POST /api/screener/run` | Start a screener run |
| `POST /api/runs` | Body `{kind: on_demand or dry_run}` |
| `GET /api/runs?limit=` and `GET /api/runs/{id}` | Run list; one run with its steps |
| `GET /api/recommendations?status=&instrument_type=&min_zone=&min_score=` | Filtered list |
| `POST /api/recommendations/{id}/approve` | Body `{mode: paper or real}`; real returns 409 "locked" |
| `POST /api/recommendations/{id}/skip` | Body `{note}` |
| `GET /api/trades/open?mode=` | Open positions |
| `GET /api/trades/log?mode=&symbol=` | Orders and fills |
| `GET /api/pnl?mode=` | Realised, unrealised, charges, by stock and total |
| `GET /api/settings` and `PATCH /api/settings` | Capital, limits, kill switch, default mode |

## 6. Interface

Screens follow the mock canvas (Trading App Screens): Sign in, Stocks, Stock detail,
Ideas, Trades (new: open trades and profit or loss with the paper / real / all filter),
Algo runs, Settings. First load uses seeded sample data from the backend so every screen
is real end to end.

## 7. Scheduler

| Job | When (India time) | Does |
|---|---|---|
| Algo run | Every 5 minutes, 09:15 to 15:30, trading days | `algo_run.run("scheduled")` |
| Paper fills | With each algo run | Fill open paper orders |
| Daily backfill | 18:30 | Fetch the day's prices, recompute metrics |
| Screener | Saturday 09:00 | Full screener run |

## 8. Build order (each task at most 6 hours, tests first)

| ID | Task |
|---|---|
| V2.1 | Scaffold `v2/backend` and `v2/ui`, tooling, CI job, empty app that serves health |
| V2.2 | `core/metrics.py` |
| V2.3 | `core/financials.py`, `core/scoring.py` |
| V2.4 | `core/zones.py`, `core/plan.py` |
| V2.5 | `core/risk.py`, `core/charges.py`, `core/pnl.py` |
| V2.6 | Database models, migrations, repositories, seed data |
| V2.7 | Price and financials adapters |
| V2.8 | Screener service and API |
| V2.9 | Algo run service, run log, API |
| V2.10 | Paper broker, trading service, portfolio service, API |
| V2.11 | Auth and settings API |
| V2.12 | UI: sign in, stocks, stock detail |
| V2.13 | UI: ideas, trades, algo runs, settings |
| V2.14 | Scheduler, end-to-end journeys, deploy to Railway |

Each task starts by committing its failing tests from `TEST_PLAN.md`, then the code that
makes them pass.
