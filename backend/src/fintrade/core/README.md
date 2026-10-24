# fintrade.core

Pure domain logic. No network, DB, or system clock. Imports nothing from `adapters` or `services`.

| Module | Public API |
|---|---|
| `errors` | `FintradeError`, `InvalidInputError`, `ConfigError`, `DataError`, `StaleDataError`, `BrokerError`, `RuleViolation(code, detail)` |
| `timezone` | `IST`, `ensure_ist(dt)`: rejects naive datetimes |
| `money` | `Rupees` (= `Decimal`), `rupees(value)`: rejects floats, `round_rupees`, `to_paise`, `from_paise` |
| `redaction` | `redact_mapping`, `redact_value`, `redact_processor` (structlog), `is_sensitive_key` |

Tests: `backend/tests/unit/core/`.
