# v2 Architecture

**Status: DRAFT, waiting for owner approval.** Date: 2026-11-17.
Stack decided in `DECISIONS.md` (2026-11-17): one Python service on Railway that also serves
a React single-page app; Railway Postgres for data (owner decision, 2026-11-19). Sign-in
was planned on Supabase Auth and is to be re-decided; mentions of it below are the old plan.

## 1. Shape

```
                        ┌──────────────────────── one Railway service ────────────────────────┐
Browser (React SPA) ───►│ FastAPI                                                             │
  email + password      │  /api/*  JSON API (auth required)                                   │
  via Supabase Auth     │  /       built React files                                          │
                        │                                                                     │
                        │ Scheduler (APScheduler)                                             │
                        │  every 5 min in market hours: algo run                              │
                        │  18:30 daily: price backfill + metrics                              │
                        │  weekly: screener                                                   │
                        │                                                                     │
                        │ services ──► core (pure rules) ──► ports ◄── adapters               │
                        └───────────────────────────────┬─────────────────────────────────────┘
                                                        │
                    Railway Postgres  ◄─────────────────┤──► Price source (public now, broker later)
                    Supabase Auth                       └──► Paper broker (in-process)
                                                             Real broker adapter (locked stub)
```

## 2. Repository layout

```
v2/
  docs/                 PRD, ARCHITECTURE, DESIGN, TEST_PLAN
  backend/
    pyproject.toml      uv, ruff, mypy strict, pytest, coverage 100% line + branch
    src/steady/
      core/             pure logic, no I/O, no clock, no network
        metrics.py        reference high, drawdowns, recovery stats, volatility
        financials.py     financial checks
        scoring.py        stability score, evidence score, "needs data"
        zones.py          buy zones and levels
        plan.py           stepped plan, cash / future / combo
        risk.py           limits check
        pnl.py            positions, realised and unrealised profit or loss
        charges.py        brokerage and statutory charges
        types.py          typed models (Pydantic / dataclasses)
      ports/            interfaces: PriceSource, FinancialsSource, Broker, Clock, Repos
      adapters/
        prices_public.py  public price source (stopgap)
        financials_file.py  CSV / manual entry import
        broker_paper.py   fills from fetched prices
        broker_real_locked.py  refuses every order
        db/               SQLAlchemy models, repositories, Alembic migrations
        auth_supabase.py  verifies Supabase JWT, allow-list
      services/
        screener.py       refresh prices, metrics, scores
        algo_run.py       detect zones, build recommendations, propose exits, write run log
        trading.py        approve / skip, place order, apply fills
        portfolio.py      open trades and profit or loss views
      api/              FastAPI routers, request / response schemas
      scheduler.py
      main.py
    tests/              unit, service, API, property tests (see TEST_PLAN.md)
  ui/
    package.json        pnpm, TypeScript strict, Vite, React, TanStack Query, Vitest
    src/
      api/              typed client generated from the OpenAPI schema
      pages/            SignIn, Stocks, StockDetail, Ideas, Trades, Runs, Settings
      components/
    tests/
  e2e/                  Playwright journeys against a seeded backend
```

Import rules (enforced with import-linter, as in `ENGINEERING.md`): `core` imports nothing
from `adapters`, `services` or `api`; `services` depend on `ports`, never on a concrete
adapter; `api` depends on `services`.

## 3. Components

| Component | Responsibility | Fails how |
|---|---|---|
| Auth | Verify the Supabase session token on every API call; allow one email | 401; lockout after repeated failures |
| Price source | Daily bars and latest price per symbol | Marks data stale; runs make no new recommendations |
| Financials source | Yearly and quarterly figures per company | Missing fields become "needs data" |
| Screener service | Compute metrics and scores; update the stock table | Per-stock errors are logged; other stocks continue |
| Algo run service | For approved stocks: zone, plan, risk check, recommendation, exit proposals | Any failed pre-check ends the run with no orders |
| Trading service | Turn an approved recommendation step into an order; apply fills | Order rejected with a reason; nothing partial |
| Paper broker | Fill orders from fetched prices with slippage and charges | Order stays open until a fresh price exists |
| Real broker (locked) | Present so the mode exists end to end | Always rejects: "real trading is locked" |
| Portfolio service | Positions, profit or loss, filters | Read-only |
| Scheduler | Start runs on time; skip when the market is closed | Missed run is logged and alerted |

## 4. Data flow of one algo run

1. Load approved stocks and settings.
2. Pre-checks: prices fresh, kill switch off, drawdown limit not hit. Any failure ends the
   run with a logged reason.
3. For each stock: compute the reference high, distance below, and zone.
4. If in a buy zone and the step is not already taken: build the plan step, choose cash or
   futures, run the risk check, and write a recommendation.
5. If a position exists: check target and hard exit; write an exit recommendation if hit.
6. Expire older recommendations that no longer apply.
7. Write the run log (ordered steps) and a summary.

Every step is written to `run_steps`, which is what the "Algo runs" screen shows.

## 5. Modes

| Mode | Orders go to | Available in this build |
|---|---|---|
| Paper | In-process paper broker using fetched market prices | Yes, default |
| Real | Broker adapter | No. The adapter is a stub that rejects every order |

Mode is stored on every order, fill and position, so every view can filter by it and paper
results can never be mixed into real totals.

## 6. Security

- Sign-in and password storage are handled by Supabase Auth; the app never stores passwords.
- The API accepts only tokens for the allow-listed email.
- Secrets (database URL, Supabase keys, later broker keys) live in Railway environment
  variables and a git-ignored local `.env`. Nothing secret is committed or logged
  (`AGENTS.md` section 7).
- Row-level security on Supabase tables as a second layer; the service uses a server key.
- No account data, holdings or personal details in the repository.

## 7. Reliability rules

- **Fail closed:** stale or missing prices mean no new recommendations and no fills.
- **Idempotent runs:** a run for the same time slot does not create duplicate
  recommendations or orders.
- **Append-only logs:** runs, steps, orders and fills are never edited or deleted.
- **One retry** on a failed external fetch, then mark as failed.
- **Kill switch:** one setting blocks all new entry orders; exits still work.

## 8. What changes later, without redesign

| Later | Change |
|---|---|
| Broker chosen | Add a price adapter and a real broker adapter behind the existing ports |
| Real trading unlocked | Replace the locked stub; add password re-check and the broker's IP requirements |
| Learned confidence | Add a model service that reads the recommendation and outcome tables |
| More algos | Add a strategy module that returns the same recommendation type |
