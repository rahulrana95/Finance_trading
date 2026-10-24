# System Architecture (v1)

Source: our own docs plus the parts we adopted from the reference guide
"Automated Option Selling & Analysis Engine" (see the review at the end of this file).

## Design principles

- **Our timing is slow:** one decision per day plus a check every 30 min. We do not need
  sub-100 ms latency or tick-by-tick storage. Reliability matters far more than speed.
- **Start simple:** one Python application with 4 separate modules. Split them into
  separate services only if needed later.
- **The risk module is independent:** it can always close positions, even if the
  strategy or ML module crashes.

## The 4 modules

```
 ┌──────────────────┐   ┌───────────────────────┐
 │ A. Data          │──▶│ B. Analytics &        │
 │ Dhan (primary)   │   │    Strategy           │
 │ AngelOne (backup)│   │ Greeks, features,     │
 │ cross-check      │   │ L0 rules, L1/L2 ML    │
 └────────┬─────────┘   └───────────┬───────────┘
          │                         │ suggestion
          ▼                         ▼
 ┌──────────────────────────────────────────────┐
 │ C. Execution & Risk                          │
 │ AGENTS.md / RULES.md checks, ledger,         │
 │ order safety, stops, kill switch             │
 └────────────────────┬─────────────────────────┘
                      ▼
 ┌──────────────────────────────────────────────┐
 │ D. Alerts: Telegram, email, voice call       │
 └──────────────────────────────────────────────┘
```

### A. Data ingestion
- **Primary:** DhanHQ. Trading API free; Data API paid (~₹499 + GST / month; verify the
  current price). Live feed via WebSocket, option chain with Greeks, OI, bid/ask.
- **Backup:** AngelOne SmartAPI (free) for cross-checking prices. Shoonya (Finvasia) is
  another free option.
- Pull the option chain **every 30 min** and just before any order (not every 3 s; we
  don't need it, and it stays well inside Dhan's rate limits).
- Cross-check primary vs backup. A mismatch or stale data means no new orders
  (`AGENTS.md` §2).

### B. Analytics and strategy
- Greeks / IV calculated by us (Black-Scholes) and checked against the broker's values
- Features: PCR and PCR momentum, OI build-up / unwinding at strikes, max pain, IV skew,
  India VIX, trend (MACD, EMAs), regime (HMM, see `ML.md`)
- L0 rules engine proposes trades; L1 / L2 models filter and size them (`ML.md`)
- Output: one suggestion per day, plus exit signals

### C. Execution and risk
- Every suggestion passes the `AGENTS.md` / `RULES.md` checks before any order
- Own position ledger, reconciled with the broker every 30 min (`MONITORING.md`)
- Safe leg order: hedge first on entry, short first on exit
- Stop-loss, drawdown limits, margin monitor, kill switch
- **Not adopted:** "delta-neutral hedging" with futures or extra options. Our rules allow
  Nifty spreads only. Delta is managed by closing or adjusting within `RULES.md`.

### D. Alerts
| Level | Channel |
|---|---|
| Info / daily summary | Telegram |
| Warning | Telegram |
| Critical (stop hit, limit breach, ledger mismatch, data failure) | Telegram **+ automated voice call** (e.g. Twilio) |
| Backup | Email |

The voice call matters because you only check 1–2 times a day.
WhatsApp (Meta Cloud API) is optional later.

## Storage

| Data | Store | Why |
|---|---|---|
| Ledger, orders, fills, decisions, logs | PostgreSQL (append-only tables) | Must be transactional and never lost |
| 30-min snapshots, option chain history, features | TimescaleDB (Postgres extension) or Parquet files | Time-series, large, used for backtests and ML |
| Live state cache | In memory for now; Redis only if needed later | We are not latency-bound |

## Python packages (planned)

- Core: `pandas`, `numpy`, `scipy`
- Broker: `dhanhq` (primary), AngelOne `smartapi-python` (backup)
- ML: `lightgbm`, `hmmlearn`, `scikit-learn`
- Features (to test): `smartmoneyconcepts` (order blocks)
- Alerts: Telegram Bot API, `twilio`
- To evaluate: OpenAlgo (self-hosted multi-broker bridge) for broker switching and failover

---

## Review of the reference guide: what we took and what we didn't

| Item in the guide | Decision | Reason |
|---|---|---|
| 4 decoupled modules (Data, Analytics, Execution & Risk, Alerts) | ✅ Adopt | Clean separation; risk can run alone |
| Sub-100 ms latency, ticks every 3 s | ❌ Not needed | We decide daily and check every 30 min |
| Dhan as primary | ✅ Adopt | Matches our choice |
| AngelOne as free backup feed | ✅ Adopt | Gives us the second source `ML.md` §5 needs |
| Zerodha Kite | ❌ Skip | ₹2,000 / month, no advantage for us |
| Redis + TimescaleDB / QuestDB | ⚠️ Partly | Postgres + TimescaleDB / Parquet yes; Redis not yet |
| Greeks, max pain, PCR momentum, OI unwinding | ✅ As ML features | Must prove value in backtest |
| Order blocks / Smart Money Concepts | ⚠️ Feature only, never a rule | Subjective, weak evidence; has a look-ahead trap (below) |
| Hard-coded risk circuits | ✅ Already in `AGENTS.md` | |
| Delta-neutral hedging | ❌ Skip | Outside our allowed instruments |
| Telegram / email / voice call alerts | ✅ Adopt | Voice for critical only |
| HMM regimes (trending / sideways / high-vol) | ✅ Adopt in `ML.md` | Good regime filter; must avoid look-ahead |
| LightGBM strike-breach probability | ✅ Already planned | Same as our touch-probability model |
| "Sell only in sideways regime" | ⚠️ Modified | Too strict; we choose structure by regime instead |
| TFT / Darts / US markets section | ❌ Skip for now | Not our market; US cues only as features |
| OpenAlgo | 🔍 Evaluate | Could simplify broker failover |

### Look-ahead traps found in the guide

1. **Order block code (swing length 5):** a swing high or low is only confirmed **5 candles
   later**. Using it on the day it forms uses future data. The signal must be shifted by
   the swing length before use.
2. **HMM regimes:** the standard "decode the whole history" method (Viterbi / smoothed
   probabilities) uses future data. We use **filtered** probabilities only, which use past
   data up to the decision day.

Both would make a backtest look much better than live trading.

Also note: the code block in the guide is collapsed onto one line and will not run as
printed. It needs reformatting and the shift fix above.
