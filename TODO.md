# TODO: Milestones and Tasks

**Rules for this list**
- Every task is **≤ 6 hours**. Bigger tasks get split.
- Every code task ships with its tests (`TESTING.md`): 100% line + branch coverage,
  positive, negative and edge cases. A task is not `done` until CI is green.
- Commit messages and branches start with the task ID, e.g. `T2.3: Black-76 Greeks`.
- Owner: **Claude** (builds) or **You** (decides / sets up accounts / reviews).
- Status: `todo` · `doing` · `review` · `done` · `blocked`

## ▶ Now working on

| Task | Milestone | Branch / change | Owner |
|---|---|---|---|
| T1.3 NSE bhavcopy downloader (PR open) | M1 | `T1.3-bhavcopy-downloader` | Claude |
| T1.4a Bhavcopy parser (PR #3) | M1 | `T1.4a-bhavcopy-parser` | Claude |
| T1.4b Data validator (PR #4) | M1 | `T1.4b-data-validator` (stacked on T1.4a) | Claude |
| T1.5 Parquet store (PR #5) | M1 | `T1.5-parquet-store` | Claude |
| T2.1a Instruments model (PR #6) | M2 | `T2.1a-instruments` | Claude |
| T2.1b Contract specs from data (PR #7) | M2 | `T2.1b-contract-specs` | Claude |
| T2.2 Market calendar (PR #8) | M2 | `T2.2-market-calendar` | Claude |
| T2.3 Greeks / IV (PR #9) | M2 | `T2.3-greeks` | Claude |
| T2.4 QuantLib cross-check (PR #10) | M2 | `T2.4-quantlib-crosscheck` (stacked on T2.3) | Claude |
| Full download 2019 → today (after merge) | M1 | run, no code | Claude |
| T1.2 Send quote requests (Accelpix, TrueData, Global Datafeeds) | M1 | — | You |

---

## M0. Planning and foundations

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T0.1 | Goal, rules, guardrails, architecture docs | — | Claude | done |
| T0.2 | Owner decisions round (14 questions) → `DECISIONS.md` | — | You + Claude | done |
| T0.3 | Repo skeleton per `ENGINEERING.md` §6: `backend/` (uv, ruff, mypy strict, pytest + 100% branch coverage), `make` targets. (UI scaffold moved to T8.1) | 4h | Claude | done |
| T0.4 | CI on GitHub Actions: lint, typecheck, tests, **coverage gate 100% line + branch**, fails on any skip | 4h | Claude | done |
| T0.5 | Test framework: pytest, xdist, hypothesis (deterministic CI profile), time-machine, `tests/support/` | 3h | Claude | done |
| T0.6 | Secrets handling: `.env.example`, git-ignore, secret scan in CI (gitleaks) | 2h | Claude | done |
| T0.8 | `import-linter` boundaries, pre-commit hooks, dependency audit, complexity limits | 3h | Claude | done |
| T0.9 | Core utils: `Clock`, money (`Decimal`), structlog setup with redaction filter, error hierarchy | 5h | Claude | done |
| T0.10 | `limits` module + test that it matches the `AGENTS.md` §1 table | 3h | Claude | done |
| T0.7 | Create Telegram bot (@BotFather); decide on domain | 1h | You | todo |

## M1. Historical data

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T1.1 | Research sources (Dhan expired options, NSE bhavcopy, paid minute vendors): years, granularity, bid/ask, cost → `DATA_SOURCES.md` | 4h | Claude | review |
| T1.2 | Pick source | — | You | todo |
| T1.2b | Confirm the go / no-go bar for the backtest (`ARCHITECTURE.md` §12) | — | You | done |
| T1.3 | NSE bhavcopy downloader: both formats, resumable, SHA-256 manifest, limited retries | 5h | Claude | review |
| T1.4a | Bhavcopy parser: both formats → one normalized daily bar (Nifty options + futures), strict schema check | 5h | Claude | review |
| T1.4b | Data validator: gaps, bad prices (high < low, negative), duplicates, expiry checks, report | 5h | Claude | review |
| T1.5 | Store as Parquet (one file per day, source checksum) + loader API + build CLI | 4h | Claude | review |

## M2. Core domain (pure logic, no network)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T2.1a | Instruments model: option contract, leg, credit spread, iron condor, with structure validation | 4h | Claude | review |
| T2.1b | Lot size + expiry history derived from data (OI gcd per expiry), checked vs UDiFF lot sizes | 4h | Claude | review |
| T2.1c | Lot size timeline from the full 2019→today data: neighbour-expiry consensus, revision dates, resolve UNKNOWN / long-dated monthlies; owner spot-check | 4h | Claude | todo |
| T2.2 | Market calendar: NSE holidays, Tuesday expiry, shifted expiries, "next week's expiry" rule | 4h | Claude | review |
| T2.3 | Greeks wrapper on `vollib` (Black-76; py_vollib is deprecated): forward from put-call parity, IV, delta/gamma/theta/vega | 5h | Claude | review |
| T2.4 | Greeks cross-check vs QuantLib + golden values + edge cases (deep OTM, near expiry, no IV solution) | 4h | Claude | review |
| T2.5 | Cost model: brokerage, STT, exchange fees, GST, stamp duty, slippage (Groww schedule) | 4h | Claude | todo |
| T2.6 | Position P&L and max-loss calculator per position and portfolio | 4h | Claude | todo |

## M3. Rules and risk engine (guardrails in code)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T3.1 | Rule checks for every `AGENTS.md` §1 limit (delta, structure, expiry, counts, margin) | 6h | Claude | todo |
| T3.2 | Risk budget tracker: weekly / monthly / yearly loss, remaining budget, max-loss vs budget | 5h | Claude | todo |
| T3.3 | Entry filters: min credit, events, time window, VIX bands (parameters from config) | 4h | Claude | todo |
| T3.4 | Exit rules: profit target, 2× stop, strike touch, time exit, budget breach | 5h | Claude | todo |
| T3.5 | Kill switch + fail-closed checks (stale data, ledger mismatch) | 3h | Claude | todo |

## M4. Backtester (rules only, L0)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T4.0 | Spike: evaluate NautilusTrader for backtest + live parity with Indian options data | 2h | Claude | todo |
| T4.1 | Replay engine (if T4.0 says build our own): steps through history, no look-ahead (guard tests) | 6h | Claude | todo |
| T4.2 | Fill simulator: bid/ask + slippage + costs | 4h | Claude | todo |
| T4.3 | Candidate generator: 9 candidates/day (3 structures × 3 deltas) × widths | 5h | Claude | todo |
| T4.4 | Counterfactual results for every candidate | 4h | Claude | todo |
| T4.5 | Metrics report: return, max DD, worst week/month, trades, win rate, avg win/loss | 4h | Claude | todo |
| T4.5b | P&L attribution: theta, delta, gamma, vega, costs per trade | 4h | Claude | todo |
| T4.6 | Walk-forward parameter search (width, min credit, target, delta, MACD on/off, VIX bands) | 6h | Claude | todo |
| T4.7a | Stress grid: re-price book for spot / IV / time shocks + collateral stress | 5h | Claude | todo |
| T4.7b | Volatility surface fit (SVI) for strike selection on thin quotes. IV only from OTM side and prices ≥ 1 tick (₹0.05), per T2.3/T2.4 findings | 6h | Claude | todo |
| T4.7c | Conservative bid/ask model when historical quotes are missing | 4h | Claude | todo |
| T4.7d | Overfitting statistics: deflated Sharpe, CSCV, bootstrap intervals | 5h | Claude | todo |
| T4.7e | Cross-check a few results against AlgoTest / Opstra | 3h | Claude | todo |
| T4.7f | Run tracking (MLflow or run table): data hash, params, results | 4h | Claude | todo |
| T4.7 | Baseline results vs go / no-go bar (`ARCHITECTURE.md` §12); approve parameter set | 2h | You | todo |

## M5. Live data (Dhan) and storage

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T5.1 | Verify Dhan TOTP login rules for data API; Groww read-only trade book API | 3h | Claude | todo |
| T5.2 | Dhan auth + session manager (TOTP if allowed, else manual-login flow + alert) | 5h | Claude | todo |
| T5.3 | Feed gateway: WebSocket, reconnect, stale detection, normalized ticks | 6h | Claude | todo |
| T5.4 | Option chain + Greeks snapshot (30 min), cross-check vs our Greeks | 4h | Claude | todo |
| T5.5 | Supabase schema: bars, snapshots, ledger, journal (append-only), RLS | 5h | Claude | todo |
| T5.6 | Ingest: Redis latest state, 1-min bars to Postgres, daily Parquet archive | 5h | Claude | todo |
| T5.6b | Margin estimate: broker margin API or SPAN-file estimate | 4h | Claude | todo |
| T5.7 | Railway deploy: services, Redis, health checks, logs | 4h | Claude | todo |

## M6. Daily decision and trade ticket (paper)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T6.1 | Feature builder shared by backtest and live (parity test: same input → same output) | 6h | Claude | todo |
| T6.2 | Entry engine at 10:00: candidates → rule filter → choose → size | 5h | Claude | todo |
| T6.3 | Trade ticket: legs, limit prices, broker SL levels → UI + Telegram | 4h | Claude | todo |
| T6.4 | Journal: decision with all candidates, reasons, features, model versions | 4h | Claude | todo |
| T6.5 | Paper fill simulator from live bid/ask | 4h | Claude | todo |

## M7. Position manager, monitoring, alerts

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T7.1 | Ledger: positions per leg with position IDs | 4h | Claude | todo |
| T7.2 | Fill import from Groww (API or contract note) + manual entry, matched to suggestion | 6h | Claude | todo |
| T7.3 | 1-min checks: stops, targets, budget; 30-min snapshot | 5h | Claude | todo |
| T7.4 | Alerts: Telegram, levels, dedupe | 4h | Claude | todo |
| T7.5 | Alarm escalator: voice call (Twilio) repeat until acknowledged | 4h | Claude | todo |
| T7.6 | Heartbeat + daily summary at 15:30 | 3h | Claude | todo |

## M8. UI (Vercel + Supabase)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T8.1 | `ui/` scaffold (pnpm, TS strict, ESLint, Prettier, Vitest 100%) + Next.js app, Google login, allowlist, `/api` proxy to Railway with secret header | 5h | Claude | todo |
| T8.2 | Live page: positions table, P&L, risk gauges, kill switch (Realtime) | 6h | Claude | todo |
| T8.3 | Trades history page | 4h | Claude | todo |
| T8.4 | Performance page: week / month / year, equity + drawdown, vs baselines | 6h | Claude | todo |
| T8.5 | Decisions & review page (outcome + process labels) | 4h | Claude | todo |
| T8.6 | System health page | 3h | Claude | todo |
| T8.7 | Tax export (P&L, turnover, charges) | 4h | Claude | todo |

## M9. News engine

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T9.1 | Event calendar (RBI, Budget, Fed, CPI, holidays) + loader | 4h | Claude | todo |
| T9.2 | Official sources: NSE / BSE / RBI / SEBI / PIB RSS collectors | 5h | Claude | todo |
| T9.3 | Trial 2 news APIs for 2 weeks; compare | 3h + 2 wk | Claude + You | todo |
| T9.4 | LLM classifier (type, severity, direction) + risk score + hard gate | 5h | Claude | todo |

## M10. ML layer (L1 + L2)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T10.1 | Labels: touch, profit-before-stop, realized vol, range | 4h | Claude | todo |
| T10.2 | HMM regime (filtered only) | 5h | Claude | todo |
| T10.3 | Volatility + range forecast vs HAR / GARCH baseline | 6h | Claude | todo |
| T10.4 | Touch-probability model (LightGBM, calibrated) | 6h | Claude | todo |
| T10.5 | Meta-model take / skip / size | 6h | Claude | todo |
| T10.6 | Purged walk-forward evaluation + acceptance report | 5h | Claude | todo |
| T10.7 | Model registry + shadow mode + drift fallback | 5h | Claude | todo |

## M10b. Operations

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T10b.1 | Runbooks: feed down, Groww down, Dhan login failed, Supabase down, ledger mismatch | 4h | Claude | todo |
| T10b.2 | Backups: Supabase PITR, Parquet second copy, monthly restore test | 3h | Claude | todo |
| T10b.3 | Sentry + uptime monitoring + scheduler missed-run alerts | 4h | Claude | todo |
| T10b.4 | Open emergency hedge cash balance at Dhan (₹1–2 L) | 1h | You | todo |
| T10b.5 | Strategy decay check (live vs backtest range) | 4h | Claude | todo |

## M11. Paper trading (8 weeks)

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T11.1 | Go-paper checklist (all tests green, alerts tested, kill switch tested) | 2h | Claude + You | todo |
| T11.2 | Weekly review during paper period (8×) | 1h each | You + Claude | todo |
| T11.3 | Go / no-go for live | 2h | You | todo |

## M12. Live (manual orders) and later

| ID | Task | Est. | Owner | Status |
|---|---|---|---|---|
| T12.1 | Live with small size, owner approval | — | You | todo |
| T12.2 | Bandit / RL (`RL.md`), after L2 proven | split later | Claude | todo |
| T12.3 | Auto-exit (after 3 months live, `AGENTS.md` §3) | split later | Claude | todo |
