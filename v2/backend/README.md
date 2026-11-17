# Steady backend (v2/backend)

One Python service: the JSON API under `/api/` and the built interface for every other
address. It currently has one route, `GET /api/health`.

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

Code is in `src/steady/`, tests in `tests/`.
