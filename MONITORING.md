# Live P&L Monitoring (stops every 1 min, full snapshot every 30 min)

## The problem

With up to 5 open positions over 2 expiries, the broker shows **net quantity per
strike**, not per trade. If two of our trades share a strike, the broker merges them,
and we can no longer tell each trade's P&L from the broker screen.

## The solution: our own position ledger

We keep our own ledger. The broker is used only for prices and as a cross-check.

**Ledger: one row per leg**

| Field | Example |
|---|---|
| Position ID | `P-2026-10-27-01` |
| Structure | Iron condor |
| Expiry | 2026-11-03 |
| Leg | Short 25,800 CE |
| Qty (lots) | 2 |
| Entry price | 42.5 |
| Credit (position) | 38 points |
| Max loss (position) | 62 points × 65 × lots |
| Stop / target levels | Loss 76 pts / profit 19–27 pts |

## Every 1 minute: stop, target and budget checks from the live stream (see `ARCHITECTURE.md` M7)

## Every 30 minutes (09:30, 10:00, ... 15:30): full snapshot

1. Fetch the latest price (LTP) and Greeks for every leg in the ledger.
2. Calculate for **each position**:
   - Live P&L (₹ and % of max profit)
   - Distance of spot from each short strike (points and %)
   - Position delta / theta
   - Status vs exit rules: profit target hit? stop hit? strike touched?
3. Calculate for the **portfolio**:
   - Total open P&L and realized P&L this week / month / year
   - Remaining loss budget: weekly (₹50 K) / monthly (₹1.5 L) / yearly (₹2.5 L)
   - Total max loss of open positions vs remaining monthly budget
   - Net delta, margin used %
4. **Reconcile:** sum of ledger quantities per strike must equal the broker's net
   positions. Any mismatch raises an alert immediately.
5. Save the snapshot. These snapshots also become RL training data.

## Alerts (phone message, e.g. Telegram)

| Level | Trigger | Action |
|---|---|---|
| 🟢 Info | Profit target reached on a position | Close it (or auto-close) |
| 🟡 Warning | Spot within ~0.5% of a short strike; loss ≥ 1× credit; weekly loss ≥ 50% of budget | Check soon |
| 🔴 Critical | Stop-loss hit; weekly loss ≥ 80% of budget; ledger ≠ broker | Act now / auto-exit |

## Human vs automatic

The human checks only 1–2 times a day, so critical exits should not wait for a human:
- **Phase 1 (paper trading):** alerts only, human decides. We learn how often alerts fire.
- **Phase 2 (live):** stop-loss and budget-breach exits are automatic. Profit-taking and
  adjustments can stay manual.

## Daily summary (after 15:30)

- Each position: P&L, days held, distance to strikes, action for tomorrow
- Week / month / year P&L vs targets and budgets
- Today's decision and its reason
