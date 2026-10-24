# fintrade.core.rules

Guardrails from `AGENTS.md` / `RULES.md` as pure functions. Every check runs and every
violation is returned (stable codes), so logs show all reasons a trade was blocked.

| Module | Public API |
|---|---|
| `entry` | `check_entry(ProposedEntry, AccountState)` → `list[RuleViolation]` (empty = allowed); `EntryRule` codes |

Each `AGENTS.md` §1 limit has its own test file in `tests/unit/core/rules/limits/`.
Never delete, skip or weaken those tests (`AGENTS.md` §8).
