# fintrade.core.rules

Guardrails from `AGENTS.md` / `RULES.md` as pure functions. Every check runs and every
violation is returned (stable codes), so logs show all reasons a trade was blocked.

| Module | Public API |
|---|---|
| `strategy_config` | `EntryFilterConfig` (tunable, set by backtest + owner approval); `DEFAULT_ENTRY_FILTERS` |
| `filters` | `check_filters(FilterInputs, config)` → violations: entry window 10:00–15:00 IST, min credit % of width per side, event blackout (today / next trading day), optional VIX band |
| `exits` | `exit_reasons(ExitInputs, config)` → reasons (empty = hold): profit target, 2× credit stop, short strike touched, time exit, loss limit hit |
| `order_sequence` | `entry_sequence` (hedges first), `exit_sequence` (shorts first): `AGENTS.md` §2 |
| `gate` | `check_gate(GateInputs)`: before any order. OPEN blocked by kill switch, market closed, data > 5 min old, ledger mismatch; CLOSE always allowed |
| `entry` | `check_entry(ProposedEntry, AccountState)` → `list[RuleViolation]` (empty = allowed); `EntryRule` codes |

Each `AGENTS.md` §1 limit has its own test file in `tests/unit/core/rules/limits/`.
Never delete, skip or weaken those tests (`AGENTS.md` §8).
