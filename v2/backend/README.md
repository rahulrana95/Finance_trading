# Steady backend (v2/backend)

One Python service: the JSON API under `/api/` and the built interface for every other
address.

| Route | Returns |
|---|---|
| `GET /api/health` | Status, version and time |
| `GET /api/stocks` | The stock table: price, distance below the 6-month high, zone, recovery figures, scores and missing data |
| `GET /api/stocks/{symbol}` | One stock |

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
