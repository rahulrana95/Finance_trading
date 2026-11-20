# Steady backend (v2/backend)

One Python service: the JSON API under `/api/` and the built interface for every other
address.

| Route | Returns |
|---|---|
| `GET /api/health` | Status, version and time |
| `GET /api/stocks` | The stock table: price, distance below the 6-month high, zone, recovery figures, scores and missing data |
| `GET /api/stocks/{symbol}` | One stock |
| `GET /api/runs`, `GET /api/runs/{id}` | Algo runs with every step in plain words |
| `POST /api/runs` | Start a run (`on_demand` or `dry_run`). Answers 202 at once; the run finishes in the background |
| `GET /api/screens/latest` | The latest market-fall screen: market state, odds from past falls, and stocks in a deep fall today |
| `POST /api/screens` | Start a screen of about 500 stocks. Answers 202; it finishes in the background |
| `GET /api/recommendations` | Ideas the algo proposed, with the stepped plan. Filters: `instrumentType`, `status`, `minZone`, `minScore` |

With `STEADY_SCHEDULER=true` the algo runs once at start and then every 5 minutes, Monday to
Friday, 09:15 to 15:30 India time. Runs and ideas are kept in Postgres when
`STEADY_DATABASE_URL` is set (tables are brought up to date at start by Alembic, migrations
in `src/steady/db/migrations`); without it they live in memory and a restart clears them.
The screener also runs at 18:30 India time on weekdays, and at start if the stored screen is
older than 20 hours. Its odds are how often each outcome followed past falls of the same size
(from the 1-year high, with or without Nifty also 10% down); the method and its test are in
`BACKTEST_RESULTS.md` (2026-11-20). Each fallen stock gets a confidence: high only when Nifty is 15% or more below its 1-year
high and the stock is down 25% or more, with the evidence listed in plain words.
The algo only proposes ideas: there is no order code.

Prices are daily closes fetched from a public, unofficial source and cached for 30 minutes.
The stock list and business figures are a seed file (`src/steady/seeds/stocks.json`) until
the database exists. There is no sign-in yet, so every route is read-only.

| Command | Does |
|---|---|
| `uv sync` | Install packages |
| `uv run pytest --cov` | Tests with coverage (must stay at 100% line and branch) |
| `uv run ruff check . && uv run ruff format --check .` | Lint and format check |
| `uv run mypy` | Type check (strict) |
| `uv run uvicorn steady.main:app --port 8000` | Run locally |

Settings come from the environment:

| Variable | Meaning | Default |
|---|---|---|
| `STEADY_STATIC_DIR` | Folder holding the built interface (`v2/ui/dist`) | none: API only |
| `STEADY_VERSION` | Version string reported by the health route | `dev` |

| Folder | Contents |
|---|---|
| `src/steady/core/` | Pure rules: metrics, scores, zones |
| `src/steady/adapters/` | Price source and seed loader |
| `src/steady/services/` | Builds the stock table |
| `src/steady/api/` | Routes and response shapes |
| `src/steady/constants.py` | Every fixed name, limit and message |
| `tests/unit/`, `tests/integration/` | Unit tests and route-level tests |
