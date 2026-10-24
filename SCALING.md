# Scaling to Many Users (target: 5,000 users, 100 QPS)

## 0. Read this first: legal, before technical

Scaling to 5,000 users is easy technically. **Legally it is the hard part.** Three things
must be solved before anyone except the owner uses the platform:

| Issue | Why | What it means |
|---|---|---|
| **Giving trade suggestions to others** | In India, recommending specific trades to other people needs SEBI registration (Research Analyst or Investment Adviser). Algo strategies offered to retail clients must also go through a broker and the exchange's empanelment process under the 2026 algo framework | No sharing our suggestions with users until a registered entity provides them, or a licensed partner does |
| **Redistributing live market data** | Exchange real-time data (option prices, Greeks from broker feeds) can't be re-broadcast to other users without an exchange data-vendor licence | Each user's live prices must come from **their own broker connection**, or we show only our derived signals / delayed data |
| **Redistributing news** | News content belongs to the publisher | Show only our own signals plus links, or use a news API plan licensed for display |

Get a short consult with a SEBI-registered compliance professional before building the
multi-user part. Build the code **multi-user ready**, but launch to others only once
this is settled.

## 1. The key insight: compute once, share with everyone

Almost all heavy work is the **same for every user**:

| Work | Per market or per user? | Cost at 5,000 users |
|---|---|---|
| Live feeds, Greeks, chain metrics, breadth | **Per market** (once) | Same as 1 user |
| News engine, LLM classification | **Per market** (once) | Same as 1 user |
| Features, regime, ML scores, 9 candidates | **Per market** (once) | Same as 1 user |
| Sizing to the user's capital and risk budget | Per user | Tiny (a formula) |
| User positions, live P&L, budgets | Per user | 5,000 × ~5 positions × 4 legs = 100 K legs per minute: **< 1 second** with vectorized code |
| Alerts | Per user | Needs a queue (see below) |
| UI reads | Per user | The 100 QPS |

So the design splits into a **shared market brain** and a thin **per-user account layer**.

```
            ┌──────────── SHARED (singletons, run once) ────────────┐
            │ Feed → Analytics → Features → ML → Market signal       │
            └───────────────────────────┬───────────────────────────┘
                                        │ 1 message per minute / per decision
                                        ▼
                         Redis (latest market state) + Supabase
                                        │
          ┌─────────────────────────────┼──────────────────────────────┐
          ▼                             ▼                              ▼
  Per-user P&L / risk worker    Alert workers (queue)          API replicas (stateless)
  (batch: all users / minute)   Telegram, voice, email         behind /api proxy
```

## 2. Component-by-component plan

| Component | How it scales | Notes |
|---|---|---|
| **Feed gateway** | **Exactly one** instance (leader lock in Redis). A second one stands by and takes over if the first dies | Two active feeds would double-write data |
| **Analytics / features / ML** | One instance, scheduled jobs. Work does not grow with users | |
| **Per-user P&L & risk** | One worker computes all users every minute in one batch; add workers by sharding user IDs if needed | Vectorized (numpy / pandas) |
| **API (`/api`)** | **Stateless replicas** on Railway; scale horizontally (2 → N) | Reads from Redis / Postgres; no in-memory state |
| **Market data to the UI** | **Shared** endpoints cached for 5–60 s (CDN / Redis). 5,000 users hitting the same snapshot = 1 backend read | Biggest QPS saver |
| **Live updates** | Supabase Realtime: one **broadcast** per minute for shared data; per-user changes via user-scoped channels | Check the plan's concurrent connection limit and upgrade before launch |
| **Database** | Supabase Postgres: every table has `user_id`, indexed, with row-level security; connection pooler; partitioned time-series tables; read replica if reads grow | Writes are small: decisions are per market, fills are per user |
| **Alerts** | Queue (Redis Streams) + workers with **rate limits** per channel | Telegram bots are limited to roughly 30 messages/sec, so 5,000 alerts take ~3 min. Send the most critical first; use per-user priority |
| **Broker connections (per user)** | Each user links their own Dhan account (read-only for positions / fills; their own data feed for live prices) | Daily login per user is their responsibility; tokens encrypted at rest |
| **Secrets** | Per-user broker tokens encrypted (Supabase Vault or a KMS); never in logs | `AGENTS.md` §7 |

## 3. Load targets and testing

| Metric | Target |
|---|---|
| Sustained | 100 QPS across all APIs |
| Spike | **300 QPS for 5 min at 10:00** (everyone opens the app when the daily decision lands) |
| API latency | p95 < 300 ms |
| Live P&L freshness | ≤ 60 s behind market for all users |
| Critical alert delivery | 95% of users within 60 s; 100% within 5 min |
| Feed failover | Standby takes over in < 30 s |

Before any launch: run a **load test** (e.g. k6) with 5,000 simulated users at these
targets, plus a "kill the feed instance" and "kill an API replica" test.

## 4. Multi-user rules

- Every user has their own capital, risk budget and positions. **Global `AGENTS.md`
  limits are the maximum.** A user can choose stricter limits, never looser ones.
- Sizing: the shared signal is scaled to each user's capital and remaining budget.
- One user's failure (bad broker token, missed login) never affects anyone else.
- Admin view for the owner: number of active users, feed health, alert queue depth,
  error rates.

## 5. What to build now vs later

| Now (owner only) | Later (multi-user, after legal is settled) |
|---|---|
| `user_id` on every table, RLS on | Sign-up, onboarding, per-user broker linking |
| Shared-brain / per-user split in the code | Alert queue with rate limits |
| Stateless API, Redis latest state | Feed leader lock + standby |
| Allowlist login (owner only) | Load tests, read replica, Realtime plan upgrade |

Building these "now" items from day one costs little and avoids a rewrite later.

## 6. Observability (needed at any scale)

- Error tracking (e.g. Sentry) on backend and UI
- Metrics: QPS, latency, queue depth, feed lag, P&L job duration
- Uptime checks on `/api/health` and on the feed heartbeat
- Daily automated report: data gaps, alerts sent, failures
