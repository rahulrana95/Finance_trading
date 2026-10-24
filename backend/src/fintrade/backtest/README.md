# fintrade.backtest

Daily replay engine (decision in `DECISIONS.md`, T4.0). Uses the same `core/` code as live.

| Module | Public API |
|---|---|
| `data` | `MarketData` protocol, `InMemoryMarketData`, `GuardedMarketData` (raises `LookAheadError` for any day after the current replay day) |
| `engine` | `ReplayEngine(data, Strategy(entry, exit, fills), ExpiryCalendar, lot_sizes, BacktestConfig).run()` → `BacktestResult` (closed / still-open trades, daily `DailyPnl`, every day's `Decision`) |

The engine always enforces the `AGENTS.md` hard limits (`core.rules.entry.check_entry`),
refuses expiries with unknown lot size, and forces exits once a loss limit is hit,
whatever the strategy policies say. Charges (`core.charges`) are paid on every leg.
