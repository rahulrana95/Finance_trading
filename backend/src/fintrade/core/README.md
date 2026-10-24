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
| `instruments` | `OptionContract`, `Leg`, `Side`, `CreditSpread` (bull put / bear call), `IronCondor`, `Position`, `credit_spread(...)`: invalid structures can't be constructed |
| `pricing.black76` | `price`, `implied_vol` (None if no solution), `greeks` → `Greeks` (theta per day, vega per vol point), `time_to_expiry_years` (to 15:30 IST) |
| `pricing.forward` | `forward_from_chain(quotes, years, rate)`: median put-call-parity forward over the 5 strikes nearest the money |
| `charges` | `order_charges(side, price, qty, day, plan)` → `OrderCharges` (brokerage, STT, exchange, SEBI, stamp, IPFT, GST, `total`); `rates_on(day)` from the dated `CHARGE_SCHEDULE`; `GROWW_FNO` (₹20/order) |
| `calendar` | `TradingCalendar` (is/next/previous trading day, days between; raises outside coverage), `ExpiryCalendar.entry_expiry(today)` (≥ 6 and ≤ 13 days), `exit_deadline(expiry)` (15:00 IST, previous trading day) |
| `contract_specs` | `derive_expiry_specs(bars)` → `ExpirySpec` per expiry: lot size (STATED / INFERRED / UNKNOWN), first/last traded, `oi_gcd` check |
| `pnl` | `risk(position, entry, lot_size)` → credit / max profit / max loss (condor: wider side only); `mark_to_market`; `portfolio_max_loss`, `portfolio_mark_to_market`; missing price → `DataError` |
| `limits` | `HARD_LIMITS` (frozen): the `AGENTS.md` §1 values. A test keeps them in sync with the doc |
| `redaction` | `redact_mapping`, `redact_value`, `redact_processor` (structlog), `is_sensitive_key` |

Tests: `backend/tests/unit/core/`.
