# fintrade.core

Pure domain logic. No network, DB, or system clock. Imports nothing from `adapters` or `services`.

| Module | Public API |
|---|---|
| `errors` | `FintradeError`, `InvalidInputError`, `ConfigError`, `DataError`, `StaleDataError`, `BrokerError`, `RuleViolation(code, detail)` |
| `timezone` | `IST`, `ensure_ist(dt)`: rejects naive datetimes |
| `money` | `Rupees` (= `Decimal`), `rupees(value)`: rejects floats, `round_rupees`, `to_paise`, `from_paise` |
| `bars` | `DailyContractBar`, `ContractKind`, `OptionType`: source-independent daily bar |
| `quality.bar_checks` | `check_bar`, `check_day` → `list[Issue]` (ERROR / WARNING with stable `IssueCode`) |
| `dates` | `weekdays(start, end)` |
| `limits` | `HARD_LIMITS` (frozen): the `AGENTS.md` §1 values. A test keeps them in sync with the doc |
| `redaction` | `redact_mapping`, `redact_value`, `redact_processor` (structlog), `is_sensitive_key` |

Tests: `backend/tests/unit/core/`.
