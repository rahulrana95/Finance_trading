# Engineering Rules

How we write code. `AGENTS.md` (safety) and `TESTING.md` (tests) add to these rules.
If anything here conflicts with `AGENTS.md`, `AGENTS.md` wins.

## 1. Move fast, safely

- **TDD:** write the failing test first, then the code, then refactor. Tests are the spec.
- **Small changes:** one `TODO.md` task (≤ 6 h) = one branch = one PR. Small PRs review
  fast and break little.
- **Definition of done:** tests green, 100% line + branch coverage, lint + types clean,
  `TODO.md` updated, docs updated if behavior changed.
- **Bug hunting:** every bug found gets a failing test first, then the fix. The test stays
  forever.
- **QA review per task:** before marking `review`, re-read the diff as an attacker and as a
  tester: what input, timing or failure breaks this?

## 2. Token and time efficiency (for AI agents)

- Small, focused files (target ≤ 300 lines, hard limit 500). Agents read less, change less.
- Each package has a short `README.md`: what it does, its public API, where tests are.
  Agents read that before opening code.
- Use `make` targets that print **only failures** (`make test`, `make lint`, `make check`),
  quiet test output (`pytest -q`), no full logs in chat.
- Don't re-read files already known; search with grep before opening files.
- Reuse existing utils and fixtures. Searching for an existing helper is cheaper than
  writing a new one.

## 3. Reuse over reinvention

- **Use proven, standard libraries**; don't hand-write what a trusted library does.
- **Library checklist** before adding a dependency: actively maintained (release in the
  last ~12 months), widely used, permissive license, typed (or has type stubs), no known
  vulnerabilities. Avoid tiny single-function packages.
- **Wrap every third-party library behind our own small interface** (adapter). We can swap
  it, test it with fakes, and keep its quirks in one place.
- **Shared utils**, not copy-paste: `backend/core/utils/` and `ui/src/lib/`; test helpers
  in `tests/support/` (factories, fakes, builders). Repeated code (3 times) becomes a util.

### Chosen libraries

| Need | Python (backend) | TypeScript (UI) |
|---|---|---|
| Package / env | `uv` (lockfile) | `pnpm` (lockfile) |
| Lint / format | `ruff` | ESLint + Prettier |
| Types | `mypy --strict` | TypeScript `strict` |
| Validation / models | `pydantic` v2, `pydantic-settings` | `zod` |
| Option pricing / Greeks / IV | `vollib` (successor of the deprecated `py_vollib`; Black-76, Jäckel "Let's Be Rational" IV); **QuantLib** as a cross-check in tests | — |
| Numbers / data | `numpy`, `pandas`, `pyarrow` (Parquet) | — |
| Money | `decimal.Decimal` (see §5) | integer paise / `decimal.js` |
| Time | `zoneinfo` (IST), `exchange_calendars` if it covers NSE well, else our calendar table | `date-fns-tz` |
| Logging | `structlog` (JSON) | — |
| HTTP / WebSocket | `httpx`, `websockets` | `fetch` |
| Retries | `tenacity` (with hard limits) | — |
| Tests | `pytest`, `pytest-xdist`, `pytest-cov`, `hypothesis`, `time-machine`, `mutmut` | Vitest, Testing Library, Playwright |
| Architecture checks | `import-linter` | `eslint-plugin-boundaries` |
| ML | `lightgbm`, `scikit-learn`, `hmmlearn` | — |
| UI | — | Next.js, `@supabase/supabase-js`, TanStack Query, shadcn/ui |

Each choice is re-checked against the checklist when the task that first needs it starts.

## 4. No magic values

- No hard-coded numbers or strings in logic. They go in one of three places:
  - **`constants`**: facts that never change at runtime (lot size history, exchange codes,
    market hours).
  - **`limits`**: the `AGENTS.md` §1 values, in one typed, frozen module. A test checks they
    match the `AGENTS.md` table, so the doc and the code can't drift apart.
  - **`config`**: tunable values (profit target %, VIX bands, widths), loaded and validated
    with `pydantic-settings`, with defaults in one file.
- Allowed literals: `0`, `1`, `-1`, and math facts used in place.
- **Exception, in tests:** expected values in golden tests are written as **literals**
  (e.g. `== 10400`), not computed from the same constants, otherwise a wrong constant
  makes a wrong test pass.

## 5. Correctness by design

- **Money is never a float.** Prices, P&L, costs and budgets use `Decimal` (or integer
  paise). Floats only for Greeks / IV / model scores, rounded at clear boundaries.
- **Time is always timezone-aware (IST)** and **injected** (a `Clock` interface), never
  read directly from the system clock in logic.
- **Validate at every boundary:** all broker, API, DB and user input is parsed into
  pydantic / zod models. Bad data is rejected with a logged reason, never passed on.
- **Immutable domain objects** (frozen dataclasses / pydantic frozen models).
- **No global mutable state.** Dependencies are passed in. Seeds fixed for anything random.

## 6. Modular architecture

Ports and adapters (hexagonal):

```
backend/
  core/        pure domain logic: instruments, calendar, greeks wrapper, costs, pnl,
               rules, risk, features, decisions. No network, no DB, no clock.
  ports/       interfaces: MarketData, Broker, Store, Notifier, Clock, NewsSource
  adapters/    dhan/, groww/, supabase/, redis/, telegram/, twilio/, news/
  services/    wiring: feed, entry engine, position manager, watchdog, api
  backtest/    replay + fill simulator, uses core/ exactly like live
```

- Dependencies point inward only: `adapters → ports → core`. `core` imports nothing from
  `adapters` or `services`. Enforced by `import-linter` in CI.
- One module = one responsibility. Public API listed in the package `README.md`.

## 7. Code quality gates (CI blocks merge)

- `ruff` lint + format, `mypy --strict` (no `Any` without a comment saying why)
- Complexity: max cyclomatic complexity 10 per function, functions ≤ ~50 lines
- 100% line + branch coverage, no skipped tests (`TESTING.md`)
- Mutation testing on `core/rules` and `core/risk`
- `import-linter` boundaries
- Dependency audit (`pip-audit`, `pnpm audit`) and secret scanning
- Pre-commit hooks run the fast subset locally

## 8. Reliability and error handling

- **Graceful ≠ keep going.** For anything that can open risk, an error means **fail
  closed**: no new trade, log it, alert. Exits keep working.
- Typed error hierarchy (`DataError`, `BrokerError`, `RuleViolation`, ...). No bare
  `except`. Never swallow an error silently.
- **Retries:** only for safe, idempotent calls, with a hard cap and backoff (`tenacity`).
  Never automatic retries for anything that changes state, except as `AGENTS.md` §2 allows.
- **Timeouts on every network call.**
- **Idempotency:** imports and journal writes use unique keys, so re-running a job never
  double-counts a fill or decision.
- Health checks and heartbeats for every long-running service.

## 9. Security (no way to exploit)

- Every API endpoint: authentication (Supabase JWT verified) + allowlist + authorization
  check, each with negative tests (no token, expired token, other user, wrong role).
- Postgres row-level security on every table; tests prove other users can't read rows.
- Input validation on everything (§5); parameterized queries only.
- Secrets only in env / secret store; a log filter redacts tokens, keys and account IDs,
  with a test that proves it.
- Pinned dependencies with lockfiles; Dependabot; audits in CI.
- Rate limits on the API; the kill-switch endpoint needs re-confirmation.

## 10. Logging

- Structured JSON logs (`structlog`): timestamp (IST), level, module, event, task/request
  ID, and the relevant IDs (position, decision, order).
- Levels used consistently: `DEBUG` dev only, `INFO` normal events, `WARNING` degraded,
  `ERROR` failed action, `CRITICAL` safety event (also alerts).
- Never log secrets or personal data (redaction filter, tested).
- Business events (decisions, fills, exits) go to the **append-only journal**, not just
  logs.

## 11. Docs

- Each package `README.md` is kept current with its public API.
- Owner decisions go in `DECISIONS.md`. Behavior changes update the relevant doc in the
  same PR.
