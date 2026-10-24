# Global Rules (v1)

These rules apply to every decision, whether a human or the model makes it.
The model (RL) may only choose actions these rules allow. Rules always win.

All ₹ figures are on ₹50 L trading capital.

---

## 1. Risk budget (most important)

| Limit | % | ₹ | On breach |
|---|---|---|---|
| Weekly loss | 1% | 50 K | Close all, no new trades until next week |
| Monthly drawdown | 3% | 1.5 L | Close all, no new trades until next month |
| Yearly drawdown | 5% | 2.5 L | Stop. Full review before restarting |
| Weekly profit target | 1% | 50 K | No new entries this week. Manage open trades only |

**Two layers of protection:**

- **Hard layer (gap-proof):** the sum of the **max possible loss** of all open spreads
  must be ≤ the **remaining monthly budget**. Spreads have a fixed max loss, so even a
  gap-up or gap-down overnight cannot breach the monthly limit.
- **Soft layer (stop-loss):** the 1% weekly limit is enforced with stop-losses checked
  every 30 minutes. A stop can slip on a gap, which is why the hard layer exists.

> Reality check: if the total max loss is ≤ 1% of capital, credits collected are usually
> only ~0.2–0.4% per week at ≤ 0.12 delta. Reaching 1% per week needs more size, which
> is only allowed because the stop-loss layer cuts losses well before max loss.

## 2. Instruments

- Nifty 50 index options only (European, cash-settled, so no early assignment)
- Defined risk only. Every short option has a long option protecting it.
- Allowed structures:
  - Iron condor (range view)
  - Bull put spread (bullish view)
  - Bear call spread (bearish view)
- Option buying: not allowed until a backtest proves it adds value.

## 3. Entry rules

- **Expiry:** always next week's expiry (the nearest expiry at least 6 days away).
  Never enter the current week's expiry.
- **Short strike:** delta ≤ 0.12 (hard limit, never above). Typical range 0.08–0.12.
- **Wing width:** fixed widths only (100 / 150 / 200 points). The backtest picks the width.
- **Minimum credit:** a set % of the wing width. The backtest tests 5–15% together with the
  width and keeps the best return per unit of worst-case loss.
  Otherwise skip.
- **Direction:** MACD (1D) plus trend filters decide IC vs bull put vs bear call.
  Until the backtest validates it, the default is an iron condor.
- **Volatility filter:** use India VIX / IV percentile.
  - Very low IV: smaller size or skip (premium too cheap for the risk).
  - Very high IV: smaller size, wider wings.
- **Events:** no new entries the day before a major event (RBI policy, Budget,
  election results, US Fed). Existing positions follow the normal exit rules.
- **Timing:** entries only after 10:00 and before 15:00 (avoid open and close spikes).

## 4. Exit rules (checked every 30 min)

Exit at whichever comes first:

1. **Profit target:** close at 50–70% of the credit received (exact % to be set by backtest).
2. **Stop-loss:** close when the loss reaches 2× the credit received (checked by the engine
   every minute). **At the broker:** right after entry, place an SL-limit buy on each short leg
   at ~2.5–3× its entry price (exact multiple set by backtest) as protection while away.
3. **Strike touch:** if spot reaches the short strike, close or adjust that side.
4. **Time exit:** close everything by **15:00 the day before expiry**. Never hold into
   expiry day (gamma risk).
5. **Budget breach:** any limit in Section 1 is hit, so close all.

## 5. Adjustment rules

- Allowed: close the tested side; roll the untested side closer for extra credit.
- Never add a naked short. Never increase total max loss to "save" a trade.
- Max 1 adjustment per position. After that, the only option is to exit.

## 6. Position limits

| Limit | Value |
|---|---|
| Open positions at once | ≤ 5 |
| Open expiries at once | ≤ 2 |
| New positions per day | ≤ 1 |
| Margin used | ≤ 60% of available margin |
| Net portfolio delta | within a set band (to be set by backtest) |

## 7. Margin and collateral

- Keep the 50:50 rule: the cash portion of margin is held in cash or a liquid ETF.
- Margin buffer: assume the MF portfolio can fall 20% in a crash. Margin used must still
  be safe after that fall (hence the 60% cap).
- Never let a margin shortfall force the sale of MF units.

## 8. Daily decision

Every trading day the system makes exactly one decision and logs it, **including
"do nothing"**:

| Action | Meaning |
|---|---|
| `NO_ACTION` | Nothing to do today (also a valid, logged decision) |
| `OPEN_IC` | Open an iron condor |
| `OPEN_BULL_PUT` | Open a bull put spread |
| `OPEN_BEAR_CALL` | Open a bear call spread |
| `ADJUST <id>` | Adjust a position (Section 5) |
| `CLOSE <id>` | Close a position |

Exits triggered by the Section 4 rules happen automatically and are not counted as the
day's decision.

## 9. Monitoring

- The system checks all open positions every 30 minutes (09:30 to 15:30, ~13 checks a day).
- The human checks 1–2 times a day and acts on alerts.
- Details: see `MONITORING.md`.

## 10. Logging (needed for review and RL)

Every decision and every exit is logged with:
- Date and time, action, position ID, all legs (strike, type, qty, price)
- Market state at decision time (see `RL.md` state list)
- Reason (which rule or signal triggered it)
- Outcome when closed: P&L, max adverse move, days held, exit reason
- Review label: right or wrong, and why
