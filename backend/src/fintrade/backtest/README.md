# fintrade.backtest

Daily replay engine (decision in `DECISIONS.md`, T4.0). Uses the same `core/` code as live.

| Module | Public API |
|---|---|
| `data` | `MarketData` protocol, `InMemoryMarketData`, `GuardedMarketData` (raises `LookAheadError` for any day after the current replay day) |
| `fills` | `BarFillModel(FillConfig, ProportionalSpread)`: reference price (settle / close / worst of both) moved against us by a modelled half-spread plus slippage, rounded to the tick against us. Bhavcopy has no bid/ask; T4.7c calibrates the `SpreadModel` |
| `candidates` | `generate_candidates(day, bars, expiry, CandidateConfig)`: every structure × target delta × width buildable from the day's chain. Short strike = OTM strike with the largest \|delta\| ≤ target; hedge `width` points out. On a coarse strike grid two targets can pick the same strike (counterfactuals de-duplicate) |
| `trades` | `open_trade(Ticket, day, bars, fills)`, `close_trade`, `settle_pnl`: one trade's fills, charges and P&L, shared by engine and counterfactuals |
| `exits` | `RuleExitPolicy(ExpiryCalendar, ExitConfig)`: `core.rules.exits` checked at each day's close; parity forward stands in for spot |
| `counterfactuals` | `counterfactuals(Simulation, days)` → `CounterfactualRun`: each distinct candidate held alone to its exit. Labels use later prices, so read them only via `known_before(day)` |
| `metrics` | `compute_metrics(capital, daily, closed)` → `Metrics`; `format_report` always puts max drawdown, worst week / month and trade count next to the return (AGENTS.md §5) |
| `engine` | `ReplayEngine(data, Strategy(entry, exit, fills), ExpiryCalendar, lot_sizes, BacktestConfig).run()` → `BacktestResult` (closed / still-open trades, daily `DailyPnl`, every day's `Decision`) |

The engine always enforces the `AGENTS.md` hard limits (`core.rules.entry.check_entry`),
refuses expiries with unknown lot size, and forces exits once a loss limit is hit,
whatever the strategy policies say. Charges (`core.charges`) are paid on every leg.
