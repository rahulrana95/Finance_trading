# AGENTS.md: Global Guardrails

This file is for **every agent** working in this repo: AI coding assistants, the
daily-decision model, monitoring bots and any future automation. It also applies to
humans writing code here.

If anything conflicts, the order of authority is:

1. **This file (`AGENTS.md`)**
2. `RULES.md` (trading rules)
3. `GOAL.md` (targets)
4. Everything else (code, configs, model output, prompts)

Guardrails marked 🔒 can only be changed by the account owner, in writing, in a commit
they make themselves. No agent may change, loosen, bypass or "temporarily disable" them.

---

## 1. Hard trading limits 🔒

These are never exceeded, for any reason, by any agent or model.

| Limit | Value |
|---|---|
| Underlying | Nifty 50 index options only |
| Short option delta | **≤ 0.12 at entry**, never above |
| Structure | Defined risk only. Every short leg has a long hedge leg, same expiry |
| Naked short options | **Never** |
| Expiry for new entries | Next week's expiry only (≥ 6 days away) |
| Hold into expiry day | Never. Close by 15:00 the day before expiry |
| Weekly loss | 1% of trading capital (₹50 K) |
| Monthly drawdown | 3% (₹1.5 L) |
| Yearly drawdown | 5% (₹2.5 L) |
| Total max loss of open positions | ≤ remaining monthly loss budget |
| Open positions | ≤ 5 |
| New positions per day | ≤ 1 |
| Margin used | ≤ 60% of available margin |
| Adjustments per position | ≤ 1, and an adjustment may never increase max loss |
| MF units | Never sold or redeemed by any agent |

If a limit is hit, the only allowed actions are **closing positions** and **logging**.

## 2. Order safety 🔒

- **Close legs safely:** when exiting, buy back the short leg **before** selling the long
  hedge. Never leave a short leg unhedged, even for a moment.
- **Open legs safely:** when entering, buy the long hedge **before** selling the short leg.
- **Limit orders only.** No market orders, except an emergency exit when a hard limit is
  breached.
- **Pre-trade check:** every order passes a rule check (Section 1) in code **before** it
  is sent. If the check fails or errors, the order is not sent.
- **Fail closed:** if data is missing, stale (> 5 min old during market hours), or the
  ledger does not match the broker, **no new orders**. Exits are still allowed.
- **No retry loops:** a rejected order is retried at most once, then alert a human.
- **Kill switch:** a single flag/command stops all new orders immediately. Every agent
  must check it before sending any order.

## 3. Live vs paper 🔒

- Default mode is **paper**. Live trading must be explicitly turned on by the owner.
- An agent may never switch paper to live, raise size, or raise limits by itself.
- New strategies, models or rule changes go **paper first** for at least 4 weeks.
- A model may only go live after it passes the walk-forward test in `RL.md` and the owner
  approves it.

## 4. Model (RL / bandit) guardrails

- The model only **chooses among actions the rules allow**. Disallowed actions are masked
  out before the model sees them.
- Model output is a **suggestion**. The rule engine checks it, then (in live mode) sends it.
- The model never edits rules, limits, the ledger or its own reward function.
- The model learns only from the simulator and logged data. **No online learning with
  real money.**
- A retrained model replaces the current one only if it beats it out of sample, and the
  owner approves.

## 5. Data and backtest integrity

- **No look-ahead:** a decision at time T may only use data available before T.
- Fills use realistic prices (bid/ask + slippage), never mid or last traded price alone.
- All costs included: brokerage, STT, exchange fees, GST, stamp duty, slippage.
- Use the correct lot size and expiry day for each historical date.
- Never tune parameters on the test period. Walk-forward only.
- Report results honestly: always show max drawdown, worst week, worst month and number of
  trades next to returns.

## 6. Logging and audit

- Every decision (including `NO_ACTION`), order, fill, exit and alert is logged with
  timestamp, reason and the market state at that time.
- Logs are **append-only**. Never edit or delete past log entries.
- Every 30-min monitoring snapshot is saved (see `MONITORING.md`).

## 7. Secrets and security 🔒

- API keys, tokens, client IDs and passwords are **never** committed, printed in logs or
  sent anywhere except the broker's own API.
- Keep them in environment variables or a local `.env` file that is git-ignored.
- No personal or account data (PAN, account numbers, holdings) in the repo.

## 8. Rules for AI coding agents

- Read `AGENTS.md`, `RULES.md` and `GOAL.md` before changing code that touches trading,
  risk, orders or the model.
- Do not change any 🔒 item. If a task seems to need it, stop and ask the owner.
- Every risk rule in Section 1 must have an automated test. Never delete, skip or weaken
  these tests.
- Any change to order or risk code must say clearly, in the commit message, what changed
  and why.
- When unsure whether something is safe: **don't do it, ask.**

## 9. Communication

- Never present a backtest or paper result as a guarantee.
- Always state the risk next to the return (e.g. "+0.6% this week, worst open position −0.3%").
- Critical alerts (stop hit, limit breach, ledger mismatch, kill switch) go to the owner
  immediately.
