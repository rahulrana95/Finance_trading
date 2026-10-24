# Testing Policy (strict)

Money is on the line. Untested code does not merge.

## 1. Coverage gate

- **100% line coverage and 100% branch coverage**, enforced in CI.
  - Python: `pytest --cov --cov-branch --cov-fail-under=100`
  - UI (TypeScript): Vitest coverage thresholds at 100 for lines, branches, functions, statements
- No `# pragma: no cover` / `istanbul ignore` except for code that truly cannot run in tests
  (e.g. `if __name__ == "__main__":`). Each exception needs a comment saying why.
- **No skipped tests** in CI. `skip` / `xfail` fail the build.
- Coverage is the minimum, not the goal: every behavior needs a test that would fail if
  the behavior broke.

## 1b. Small, parallel tests

- One test file per unit, focused, ≤ ~200 lines. Run in parallel with `pytest-xdist` /
  Vitest threads.
- Tests are independent: no shared mutable state, no order dependence, no real clock,
  no network. Any test must pass alone and in any order.
- Shared factories, fakes and builders live in `tests/support/`; never copy-paste setup.

## 2. Every unit gets four kinds of tests

| Kind | Question it answers | Example (spread max-loss check) |
|---|---|---|
| **Positive** | Does it work for valid input? | 100-pt spread, 20 credit, 2 lots → max loss = 80 × 65 × 2 |
| **Negative** | Does it reject bad input loudly? | Negative lots, missing hedge leg, hedge on wrong expiry → error, no result |
| **Edge / boundary** | Exactly at the limit? Just over? | Delta 0.12 allowed; 0.1201 rejected. Loss exactly = budget allowed; ₹1 over rejected |
| **QA / scenario** | Does a real-world flow behave correctly end to end? | Gap-down day: stop fires, short leg closed before hedge, alert sent, journal written |

## 3. Extra rules for money-critical code

Applies to: Greeks, P&L, costs, rule checks, risk budget, exits, ledger, fill import,
order sequencing.

- **Property-based tests** (hypothesis): e.g. "max loss is never negative", "adding a
  hedge never increases max loss", "P&L of a closed spread = credit − debit − costs".
- **Every `AGENTS.md` §1 limit** has its own test file with at-limit, over-limit and
  under-limit cases. These tests are never deleted, skipped or weakened.
- **Mutation testing** (mutmut) on the rules / risk modules: tests must catch changed code.
  Target: no surviving mutants in `rules/` and `risk/`.
- **Golden tests** for Greeks and costs: fixed inputs with known correct outputs
  (checked by hand or against a reference).

## 4. Time, data and look-ahead tests

- Time is always injected (no real clock in logic). Tests freeze time (freezegun).
- Every time-based rule tested at: market open, 10:00, 15:00, expiry day, holiday,
  shifted expiry, day before expiry.
- **Look-ahead guard test:** the feature builder at time T is given data that includes
  values after T; the test fails if any feature changes.
- **Backtest / live parity test:** same recorded data through backtest and live code paths
  → identical decisions.

## 5. External services

- Unit tests never call real networks. Dhan, Groww, Supabase, Telegram, Twilio and LLM
  calls are behind interfaces with fakes.
- Fakes cover failures: timeout, disconnect, bad data, rate limit, auth expired,
  partial fill, rejected order.
- A small separate set of **integration tests** runs against sandbox / paper accounts,
  not in the 100% gate, run on demand.

## 6. QA checklist before each milestone closes

- [ ] All tests green, coverage 100% line + branch
- [ ] Negative and edge cases listed in the PR description
- [ ] Failure scenarios tested (data stale, feed down, DB down, alert channel down)
- [ ] Manual QA run of the flow on recorded data, result attached
- [ ] `TODO.md` updated
