# Decisions Log

Owner decisions, newest first. Each one is reflected in the doc named.

## 2026-10-24: open-questions round

| # | Topic | Decision | Doc |
|---|---|---|---|
| 1 | Credit vs hedge width | Backtest picks width (100/150/200) and minimum credit (5–15% of width) | `RULES.md` §3 |
| 2 | Cash for 50:50 rule | ₹10 L+ cash available | `GOAL.md` |
| 3 | Collateral / broker | MFs pledged on **Groww**. Trades placed on Groww; **Dhan for data only** | `ARCHITECTURE.md` §1b |
| 4 | Exits while away | Broker stop-loss orders after every entry + repeated voice calls | `ARCHITECTURE.md` §1b |
| 5 | Broker stop type | Per-leg SL-limit on short legs at ~2.5–3× entry (multiple from backtest); engine checks the true spread stop every minute | `RULES.md` §4 |
| 6 | Strategy parameters | Backtest decides all (profit target, delta, MACD use, VIX bands, delta band); owner approves before paper | `RULES.md` |
| 7 | Historical data | Research sources, then owner picks | Open |
| 8 | Accounts | Railway Pro ✅, Supabase Pro ✅. Still needed: domain, Telegram bot | `ARCHITECTURE.md` §7 |
| 9 | Dhan daily login | Automate with TOTP if Dhan allows; else manual by 08:15 | `ARCHITECTURE.md` §1b |
| 10 | Paper trading | **8 weeks** before real money | `AGENTS.md` §3 |
| 11 | Review labels | Two labels: outcome (P&L) and process (rules + reasoning) | `ML.md`, UI |
| 12 | Tax | Has a CA; system exports yearly P&L, turnover and charges, shows after-tax returns | UI |
| 13 | Multi-user | **Personal use only** | `SCALING.md` (deferred) |
| 14 | Auto-execution | After 3 months of manual live trading with no failures; auto-exits first | `AGENTS.md` §3 |

## Earlier decisions

- Nifty 50 weekly options, next week's expiry only, defined risk only, short delta ≤ 0.12
- Trading capital ₹50 L; 40% stretch / 10% minimum per year; ≤ 1% profit target per week
- Loss limits: 1% / week, 3% / month, 5% / year
- Daily decision at 10:00; stops checked every minute; manual order placement
- Backend on Railway, UI on Vercel with same-domain `/api` proxy, Supabase (Postgres, Google login, Realtime)
- Long-term goal ₹50 Cr; never a reason to raise risk limits
