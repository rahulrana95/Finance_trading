# backend

Python engine for the Nifty option selling system. Layout follows `ENGINEERING.md` §6.

| Package | Purpose |
|---|---|
| `fintrade.core` | Pure domain logic. No network, DB or clock |
| `fintrade.ports` | Interfaces to the outside world |
| `fintrade.adapters` | Implementations of ports (Dhan, Groww, Supabase, ...) |
| `fintrade.services` | Wiring and long-running services |
| `fintrade.backtest` | Replay engine, using `core` exactly like live |

## Commands (from repo root)

| Command | What it does |
|---|---|
| `make setup` | Install dependencies |
| `make check` | Lint, format check, types, tests with 100% coverage gate |
| `make test` | Tests only (parallel), coverage gate |
| `make fmt` | Auto-format and fix lint |
