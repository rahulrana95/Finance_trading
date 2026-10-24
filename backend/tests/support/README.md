# tests/support

Shared test helpers. Reuse these; never copy-paste setup into test files (`TESTING.md` §1b).

| Module | Purpose |
|---|---|
| `clock.py` | `FixedClock` for injecting time (added in T0.9) |
| `factories.py` | Builders for domain objects (added with each domain task) |
| `fakes/` | Fake adapters for ports: broker, market data, store, notifier (added with each port) |
