# System Architecture (v2, draft for review)

## 0. The problem we are solving

Every trading day, at a fixed time (10:00), answer one question with as much accuracy
as possible:

> **"Given everything we know right now, should we sell a far call spread, a far put
> spread, both (iron condor), or nothing? And at what size?"**

Then, for every open trade, every minute until it closes:

> **"Hold, book profit, adjust, or exit?"**

Everything in this document exists to answer those two questions **correctly, quickly
and safely**, and to **learn from every answer** so the next one is better.

**What "better decisions" means here.** At ≤ 0.12 delta, ~88% of trades win anyway. A model
that always says "take it" is 88% "accurate". So accuracy is measured as:
1. How many of the eventual **losers** did we skip or shrink? (most important)
2. How many good trades did we wrongly skip? (cost of being too careful)
3. Worst week / worst month vs rules-only.

---

## 1. Hard truths that shape the design

These are not opinions; each one forces a design choice.

| Fact | Consequence for the design |
|---|---|
| **SEBI retail algo rules (from 1 Apr 2026):** order APIs only from a registered app on a **whitelisted static IP traceable to us** (shared / rotating IPs don't qualify). Market data APIs can come from anywhere. Daily 2FA login, ≤ 10 orders/sec. | Order traffic must leave from a **dedicated static IP**. The owner does a **daily login** each morning. We use limit orders anyway. |
| **Railway static outbound IPs (Pro plan) may be shared with other customers and balanced over several IPs.** No India region (nearest: Singapore). | Railway runs the backend, but **order calls go out through our own small static-IP server** (see §7). |
| **Vercel is serverless.** Functions are short-lived; they cannot hold a WebSocket open all day. | Vercel hosts **only the UI**. The engine runs on Railway (always-on). |
| **Historical data has no Greeks.** | We **calculate Greeks ourselves**, live and in backtests, with the same code. Broker Greeks are only a cross-check. |
| **Backtest ≠ live is the #1 way trading systems fail.** | One shared feature/Greeks/decision codebase used by **both** the backtest and live engine. |
| **News has weak predictive power for a 1-week index move,** but strong value as a **danger signal** (war, policy shock, crash). | News is used mainly as a **risk gate** (skip or shrink), not as a reason to trade. |
| **We trade at most 1 new position a day.** | "Fast" means seconds, not milliseconds. The real speed need is **exits during a fast move**. |

## 1b. Execution mode (current): MANUAL

**Brokers:** **Groww** = execution + collateral (MFs pledged there, ₹10 L+ cash for the
cash half of margin). **Dhan** = data only (live feed, option chain, Greeks). Dhan login
is automated with TOTP **if Dhan's terms allow it** (to verify); otherwise a daily manual
login before 08:15 with a critical alert at 09:10 if missing.

**The owner places all orders by hand.** The system is advisory: it decides, records
and monitors, but never sends an order. This changes four things:

| Area | Manual mode (now) | Auto mode (later, optional) |
|---|---|---|
| M8 | **Trade ticket**: the exact legs, strikes, lots and limit prices, shown in the UI and sent to Telegram at 10:00 | Order Manager sends orders |
| Fills | Orders are placed on **Groww** (MF collateral is pledged there). Fills imported from Groww's API if it offers a read-only trade book, otherwise contract note upload or manual entry in the UI; matched to the suggestion | From order responses |
| M10 | **Alarm escalator**: critical alerts repeat (Telegram → voice call → call again every 5 min) until the owner acknowledges in the UI | Can close positions itself |
| Static IP / order relay | **Not needed** | Needed (see §7) |

- The journal records both the **suggested** trade and the **actual** trade (price, time,
  any difference). Slippage from manual entry is measured, not guessed.
- If the owner skips or changes a suggestion, that is logged too. It is useful data.
- **Protection while away:** after entering, the trade ticket also lists **stop-loss
  orders to place at the broker** on the short legs (stop-limit buy at the 2× credit
  level). The broker then enforces the stop even if nobody is watching. The engine still
  checks every minute and escalates if something is wrong.

---

## 2. Big picture

```
                    ┌──────────────────────── RAILWAY (always-on backend, Singapore) ───────────────────────────┐
                    │                                                                                            │
 Dhan WebSocket ───▶│ M1 Feed Gateway ──▶ M2 Ingest & Store ──▶ Redis (latest state, pub/sub)                    │
 AngelOne (backup)─▶│      │                     │                    │                                          │
 News / RSS / NSE ─▶│ M3 News Engine ────────────┘                    ▼                                          │
 Calendar, FII/DII ▶│                                     M4 Analytics: Greeks, chain metrics, breadth           │
                    │                                                 │                                          │
                    │                                                 ▼                                          │
                    │                                     M5 Feature Builder (same code as backtest)             │
                    │                                        │                       │                           │
                    │                                        ▼                       ▼                           │
                    │                         M6 Entry Engine (10:00)      M7 Position Manager (every 1 min)     │
                    │                         candidates → ML → choose     hold / book / adjust / exit           │
                    │                                        │                       │                           │
                    │                                        └──────────┬────────────┘                           │
                    │                                                   ▼                                        │
                    │                                     M8 Risk Gate + Order Manager ──▶ ORDER RELAY ──▶ Dhan  │
                    │                                                   │             (own VM, Mumbai,       │
                    │                                                   │              dedicated static IP,  │
                    │                                                   │              also runs M10)        │
                    │      M10 Risk Watchdog (on the relay VM) ◀────────┤  can always flatten positions          │
                    │                                                   ▼                                        │
                    │                                     M9 Journal (decisions, counterfactuals, fills)         │
                    │                                                   │                                        │
                    │                                     M11 Alerts (Telegram, voice call, email)               │
                    └───────────────────────────────────────────────────┼────────────────────────────────────────┘
                                                                        ▼
                                          SUPABASE: Postgres (ledger, journal, bars, snapshots, metrics),
                                                    Auth (Google), Realtime, Storage (Parquet history, models)
                                                                        ▲
                                          VERCEL: Next.js UI (login required, read-only + kill switch)
                                                  app.<domain>/      → UI
                                                  app.<domain>/api/* → proxied to Railway backend (same domain, no CORS)

                    RESEARCH (offline, laptop or batch job): M12 Backtester + M13 Training + Model Registry
```

---

## 3. Modules

### M1. Feed Gateway (live data in)

**Job:** keep live connections open and turn every tick into one standard format.

| Feed | Instruments | Source |
|---|---|---|
| Nifty options | Current + next weekly expiry, strikes within ±1,500 pts of spot (~240 contracts) | Dhan WebSocket (full packet: LTP, bid/ask, OI, volume) |
| Nifty index + futures | Nifty 50, current-month future | Dhan |
| India VIX | | Dhan |
| Sector indices | Bank Nifty, Fin Nifty, Nifty IT, Auto, Pharma, FMCG, Metal, Energy, Realty | Dhan |
| Nifty 50 stocks | All 50 constituents | Dhan |
| Broker option chain (with Greeks) | Snapshot every 30 min, for cross-check | Dhan REST |
| Backup prices | Same core instruments | AngelOne SmartAPI |

- Reconnects automatically; marks a feed **stale** if no tick for 60 s in market hours.
- Compares primary vs backup prices; a mismatch beyond a threshold raises a data alert
  and blocks new entries (`AGENTS.md` §2).

### M2. Ingest & Store

**Job:** put data where each consumer needs it.

| Data | Where | Kept |
|---|---|---|
| Latest tick per instrument | Redis (on the trading server) | Live only |
| 1-minute bars (all instruments above) | Supabase Postgres, partitioned by day | Forever |
| Raw ticks | Parquet files, uploaded daily to Supabase Storage | 1 year, then bars only |
| End-of-day: NSE bhavcopy, FII/DII flows, event calendar | Postgres | Forever |

Size check: ~300 instruments × 375 min ≈ **110 K rows/day** of 1-min bars, ~28 M rows/year.
Fine for Postgres with daily partitions.

### M3. News Engine

**Job:** turn news into structured, timestamped risk signals.

- **Sources:** see "News sources" below.
- **Schedule:** continuous in market hours; a full sweep at **08:30** covering news since
  the previous close (overnight and global).
- **Processing:** dedupe → an LLM classifies each item into:
  - `event_type` (policy, geopolitics, macro data, earnings of a heavyweight, global market move, other)
  - `severity` 0–3, `direction` (risk-on / risk-off / neutral), affected sectors / stocks
- **Output used by the engine:**
  - `news_risk_score` for the last 30 min and the last 24 h (a feature for the ML models)
  - **Hard gate:** severity-3 risk-off news in the last 24 h means no new entry today
- Every item is stored with its original timestamp, so the backtest uses only news
  published **before** the decision time.

> Honest note: news is the least reliable input for prediction. We start it as a gate and
> a feature, and keep it only if it measurably reduces losing trades in the backtest.

#### News sources (recommended)

For an index option seller, what matters is **"is something big happening?"**, not every
headline. So the most valuable sources are the **official primary sources**: they are
free, they are first, and they are never wrong about what was announced.

| Tier | Source | What it gives | Cost | Use |
|---|---|---|---|---|
| **1. Official (must have)** | NSE RSS feeds (announcements, board meetings, results, corporate actions) | Company events for the 50 Nifty stocks, especially heavyweights | Free | Earnings / event flags per stock |
| | BSE corporate announcements | Same, second source | Free | Cross-check |
| | RBI press releases, SEBI press releases / circulars, PIB (government), MoSPI (GDP, CPI, IIP dates) | Policy and macro events | Free | Hard event gates |
| | Own event calendar (RBI policy dates, Budget, elections, Fed / FOMC, US CPI, F&O expiries, holidays) | Known risk dates, in advance | Free (maintained by us) | **Most important input of all**: known events cause most big moves |
| **2. Headlines (pick one paid API)** | A financial news API with India coverage, e.g. **Marketaux** or **EODHD** (both tag news to NSE/BSE tickers) | Broad Indian + global business headlines with timestamps and tickers | ~$20–100 / month | Breadth of coverage, LLM classification |
| **3. Global** | Same API's global feed; plus prices of GIFT Nifty, US futures, crude, USD/INR, US 10Y | Overnight global shocks | Included / price data | Pre-market risk score |
| **Avoid for now** | Reuters / Bloomberg (enterprise pricing), X / Twitter API (expensive, noisy), scraping news sites (breaks often, violates terms) | | | |

How to choose the Tier 2 vendor: **trial 2 vendors for 2 weeks in parallel** and measure
(a) delay vs the official source, (b) how many of the real market-moving events of those
2 weeks they caught, (c) duplicates and noise. Keep the one that wins. Don't decide from
marketing pages.

Note on scale: free RSS from Indian news sites (Moneycontrol, ET, etc.) is fine for
personal research only. Showing their content to other users needs a licence (see
`SCALING.md`).

### M4. Analytics: Greeks and market metrics

**Job:** compute everything derived from prices.

- **Greeks and IV, calculated by us:**
  - Forward price from **put-call parity** (synthetic future). This avoids guessing
    interest and dividend rates.
  - Black-76 model on that forward for IV, delta, gamma, theta, vega
  - Compared with Dhan's Greeks every 30 min; a large gap raises a data alert
- **Option chain metrics:** PCR (OI and volume) and its change, OI build-up / unwinding per
  strike, max pain, IV skew (put IV − call IV at equal delta), ATM IV, term structure
  (this week vs next week IV)
- **Market breadth:** Nifty 50 advance/decline, % of stocks above 20/50-day EMA, move of the
  top 10 heavyweights (they drive most of the index), sector leadership / divergence
- **Trend and range:** MACD (1D), EMA 20/50/200, ATR, opening range (09:15–10:00)
- Runs every minute on the latest Redis state. Takes milliseconds.

### M5. Feature Builder (the shared brain)

**Job:** one function, `build_features(time T)`, that produces the exact same feature set
in live trading and in the backtest, using only data available before T.

This is the single most important piece of code for reliability. If live and backtest
features differ, every backtest result is fiction.

- **Precomputed at 08:45:** daily features (trend, regime, volatility forecast, overnight
  news, global cues, FII/DII). These don't change during the day.
- **Computed at 10:00:** intraday features (opening range, first 45-min breadth, chain
  changes since open, last 30-min news).
- So the 10:00 decision only computes the small intraday part: **under 2 seconds**.

### M6. Entry Engine (runs at 10:00)

**Job:** decide today's entry, or no entry.

**Step 1: Rules generate candidates (L0).** For each structure and delta, build the
exact trade:

| Candidate | Short leg | Long hedge |
|---|---|---|
| Bear call spread | Call at delta 0.08 / 0.10 / 0.12 | 200 pts further out |
| Bull put spread | Put at delta 0.08 / 0.10 / 0.12 | 200 pts further out |
| Iron condor | Both of the above | Both hedges |

That is 9 candidates a day (plus width variants later). Candidates that fail any
`RULES.md` / `AGENTS.md` check (credit too low, event day, budget left, margin) are removed.

**Step 2: ML scores each remaining candidate (L1 + L2).** For each one:
- P(short strike touched before exit), from the L1 touch model
- P(trade hits profit target before stop or time exit), from the L2 meta-model
- Expected P&L after costs and expected worst-case loss

**Step 3: Choose.**
- Pick the candidate with the best **risk-adjusted expected P&L**.
- If none clears the minimum confidence threshold: `NO_ACTION`.
- Size from the remaining risk budget, scaled down by uncertainty (never up).

**Step 4: Record and send.** Log the decision **with all 9 candidates and their scores**
(see M9), then pass the chosen trade to M8.

If data is stale or missing at 10:00, the engine retries once at 10:30, then logs
`NO_ACTION (data)`.

### M7. Position Manager (every 1 minute)

**Job:** manage every open trade.

| Check | Frequency | Source |
|---|---|---|
| Hard stop (loss ≥ 2× credit), strike touch, budget breach | **Every 1 min** (from live stream) | Rules (`RULES.md` §4), no ML |
| Profit target (50–70% of credit) | Every 1 min | Rules |
| Time exit (15:00 day before expiry) | Scheduled | Rules |
| **ML exit score:** P(this trade ends at the stop from here) | Every 30 min | L2 exit model |
| Adjustment check | Every 30 min | Rules + ML |

- If the ML exit score is high, the position is **closed early or reduced**. ML can only
  make an exit **earlier**, never later. Hard stops are always rules.
- A 30-min snapshot of every position is saved (`MONITORING.md`); stop checks happen
  every minute. (Change from v1: a 30-min-only check could let a loss run far past the stop.)

### M8. Risk Gate + Order Manager

**Job:** the only module allowed to send orders.

- Re-runs every `AGENTS.md` §1 check right before sending. Fails closed.
- Checks the kill switch flag (Supabase + local file) before every order.
- Leg order: buy hedge → sell short on entry; buy back short → sell hedge on exit.
- Limit orders at a price derived from bid/ask; re-price a few times within a set limit;
  if not filled, cancel and alert.
- Writes every order, fill and rejection to the ledger (append-only).
- Paper mode: same path, but fills are simulated from live bid/ask instead of sent.

### M9. Journal (memory for learning)

**Job:** record everything needed to learn, review and audit.

For every decision:
- Timestamp, full feature vector, model versions
- **All candidates with their scores** and the chosen one (or `NO_ACTION`) with the reason
- Later: the **actual outcome of every candidate**, not just the one taken
  (a "counterfactual" result, simulated from real prices)
- Owner's review label (right / wrong / why) from the UI

> This is how we "find more patterns" without waiting years: each day produces **9
> labelled examples**, not 1. Over a year that is ~2,250 labelled outcomes instead of 250.
> The same is done on historical data in the backtest.

### M10. Risk Watchdog (separate process, separate machine)

**Job:** keep us safe if the main engine crashes or hangs, or Railway itself is down.

- Runs on the **order relay VM**, not on Railway, so one provider outage cannot take
  down both the engine and the safety net.
- Its own broker session.
- Every minute: reads broker positions directly, checks loss limits and expiry-day rule.
- If the main engine's heartbeat is missing for 3 min during market hours: alert. If a
  hard limit is breached and the engine is down: **closes positions itself**, safe leg order.
- Can only close. Can never open.

### M11. Alerts

| Level | Examples | Channel |
|---|---|---|
| Info | Daily summary, trade opened / closed | Telegram |
| Warning | Spot near short strike, loss ≥ 1× credit, feed lag | Telegram |
| Critical | Stop hit, limit breach, ledger mismatch, engine down, login missing | Telegram **+ voice call** |

### M12–M13. Research: Backtester, Training, Model Registry (offline)

- **Backtester:** replays history minute by minute through **the same M4–M8 code** with
  simulated fills (bid/ask + slippage + all costs).
- **Training:** walk-forward with purging; calibration; models saved with version, data
  snapshot and test report (`ML.md`).
- **Model registry:** in Supabase Storage. Live engine loads only models marked
  `approved` by the owner. New models run in **shadow mode** first.
- **Pattern mining:** search the journal + backtest results for conditions where losses
  cluster (e.g. "high VIX + falling breadth + Monday"). Each pattern found becomes a
  **candidate rule or feature**, tested on later data it was not found on. Count every
  pattern tried; many tries need stronger proof.

---

## 4. Where ML is used (and where it is not)

| Place | Model | Decides | Can it add risk? |
|---|---|---|---|
| M3 News | LLM classifier | Event type, severity, risk-on/off | No (gate or feature only) |
| M5 Features | HMM regime (filtered) | Sideways / trending / high-vol | No |
| M5 Features | Volatility forecast (HAR / LightGBM) | Expected realized vol vs IV | No |
| M6 Entry | L1 touch-probability (LightGBM) | Chance each short strike is hit | No |
| M6 Entry | L2 meta-model (LightGBM, calibrated) | Take / skip / size per candidate | Only within the risk budget; uncertainty only shrinks size |
| M7 Exit | L2 exit model | Exit earlier than rules | Only earlier exits |
| M12 Research | Pattern mining | New rule / feature ideas | Only via owner-approved rule changes |
| Later | Bandit / RL (`RL.md`) | Choose among allowed actions | Within guardrails only |

**Not ML:** hard stops, budget limits, order safety, kill switch, expiry-day exit. These
are always plain rules.

---

## 5. Daily timeline (IST)

| Time | What happens |
|---|---|
| 08:15 | Owner completes daily broker login (2FA). If missing by 09:10: critical alert |
| 08:30 | News sweep (overnight + global). Global cues pulled |
| 08:45 | Daily features + regime + vol forecast precomputed |
| 09:00–09:08 | Pre-open session data captured |
| 09:15 | Market opens. Feeds live. Position Manager active on open trades |
| 10:00 | **Entry decision** (M6). Logged with all candidates |
| 10:00–15:00 | Order placed if a trade is chosen |
| Every 1 min | Stops, targets, budget checks; heartbeat |
| Every 30 min | ML exit score, snapshot, ledger reconciliation, Greeks cross-check |
| 15:00 (day before expiry) | Time exit of expiring positions |
| 15:30 | Market close. Daily summary to Telegram |
| 16:00 | Raw ticks to Parquet. Counterfactual outcomes updated. Metrics refreshed for UI |

---

## 6. UI (Vercel + Supabase)

**Principle:** the UI shows the truth from the ledger and journal. It never places
trades. The only write actions are the **kill switch**, **review labels**, and
**approving a model / switching paper ↔ live** (owner only, with confirmation).

**Access:** Supabase Auth with Google login. **Allowlist:** only the owner's Google account
(and anyone the owner adds). Postgres row-level security; the UI uses read-only access.
The trading server's credentials never touch the UI.

**Live updates:** Supabase Realtime pushes position and P&L changes; no page refresh.
(Vercel rewrites do not carry WebSockets, so live data never goes through the proxy.)

**Same-domain proxy:**
- Vercel rewrite: `/api/:path*` → `https://<backend>.up.railway.app/:path*`. The browser
  only ever talks to one domain: no CORS, cookies stay first-party.
- The browser sends the Supabase session token; the backend **verifies the token and
  checks the allowlist on every request**. The proxy is not the security boundary.
- The backend also requires a secret header added by the Vercel proxy, so the raw Railway
  URL is useless if someone finds it.
- Use the proxy only for short requests (reviews, kill switch, reports). Long jobs run in
  the backend and report progress through Supabase.

### Pages

**1. Live (home)**
- Top bar: today's P&L, week / month / year P&L, mode (PAPER / LIVE), feed status, engine
  heartbeat, **kill switch**
- Risk budget gauges: weekly (₹50 K), monthly (₹1.5 L), yearly (₹2.5 L) used vs left;
  margin used %
- Open positions table:

| Position | Structure | Expiry | Legs (strike, CE/PE, buy/sell) | Lots | Entry price | Live price | Live P&L (₹, % of max profit) | Distance to short strike | Delta / theta | Stop / target | Exit score |
|---|---|---|---|---|---|---|---|---|---|---|---|

- Today's decision card: action, chosen candidate, scores of all 9 candidates, reason

**2. Trades (history)**
- Every closed trade: entry / exit time and price per leg, lots, P&L, days held, exit
  reason, max adverse move, model score at entry
- Filter by structure, delta, regime, exit reason

**3. Performance**
- Equity curve and drawdown curve
- Tables by **week / month / year**: P&L (₹ and %), number of trades, win rate, average win,
  average loss, worst trade, worst week, max drawdown
- **Model vs baselines:** our live result vs rules-only vs "always iron condor", on the same
  days (from counterfactuals)
- Model quality: calibration chart, losers skipped vs winners skipped

**4. Decisions & Review**
- Daily decision log including `NO_ACTION` days
- Owner marks each closed decision **right / wrong + reason**. Feeds training (M9)

**5. System health**
- Feed latency, stale feeds, primary vs backup price gaps, Greeks cross-check gaps
- Last ledger reconciliation result, model versions in use, alerts log

---

## 7. Deployment and cost (estimate, verify before buying)

| Component | Where | Approx. monthly cost |
|---|---|---|
| Backend: M1–M9, M11, Redis, scheduled jobs, `/api` | **Railway** (Pro plan; Singapore region, nearest to India) | Railway Pro + usage |
| Order relay + M10 watchdog | Small VM in **Mumbai** with a **dedicated** static IP (e.g. AWS Lightsail ap-south-1). **Deferred: manual mode now** | ~₹500–1,000 (later) |
| News API (Tier 2) | Marketaux or EODHD after a 2-week trial | ~$20–100 |
| Dhan Data API | Dhan | ~₹499 + GST |
| AngelOne SmartAPI (backup) | AngelOne | Free |
| Database, auth, realtime, storage | Supabase (Pro plan) | ~$25 |
| UI | Vercel (existing) | Existing plan |
| News LLM classification | Claude API | Small (a few hundred items/day) |
| Voice / SMS alerts | Twilio | Small (only critical alerts) |

### Why a separate order relay (only for auto mode; **not needed while orders are manual**)

Railway's static IPs may be shared with other customers, and SEBI wants an IP traceable to
us. So only the **order traffic** goes through our own VM:

- The relay is tiny: an authenticated HTTPS forward proxy (TLS end to end, so it only
  passes encrypted traffic) or a small order service. Railway → relay → Dhan order API.
- Market data (WebSocket, option chain) goes directly from Railway to Dhan; it does not
  need the static IP.
- Register the relay's IP with Dhan (plus a secondary IP if Dhan allows one).
- The same VM runs the M10 watchdog, which gives us a second provider for safety.
- If the relay is down: no new entries (fail closed) and a critical alert. The watchdog on
  the same VM is unaffected by a Railway outage.

**Simpler alternative:** run everything on one Mumbai VM and skip Railway. Fewer moving
parts, but we manage the server ourselves. Railway + relay is chosen because deploys,
logs and restarts are easier on Railway.

Tech: Python for the engine (asyncio for feeds, LightGBM / hmmlearn for ML), Redis on
Railway, Next.js + TypeScript for the UI.

---

## 8. Build order

| Phase | Build | Done when |
|---|---|---|
| 1 | M1 + M2: feeds and storage | 2 weeks of clean 1-min data with no gaps |
| 2 | M4 + M5: Greeks and features | Our Greeks match Dhan's within tolerance |
| 3 | M12: backtester on historical data, rules only (L0) | Baseline numbers with drawdowns |
| 4 | UI pages 1, 2, 5 (paper data) | Owner can see live paper positions |
| 5 | M6 + M7 + M8 + M10 in **paper mode** | 4+ weeks paper, journal complete |
| 6 | M3 news + L1 / L2 models in shadow mode | Beat rules-only out of sample |
| 7 | Live with small size, owner approval | All `AGENTS.md` checks green |
| 8 | Bandit / RL (`RL.md`) | Beat L2 out of sample |

---

## 9. Review of the reference PDF (kept from v1)

| Item | Decision |
|---|---|
| 4 decoupled modules | ✅ Expanded into M1–M13 |
| Sub-100 ms latency, 3-s chain refresh | ❌ Not needed; seconds are enough. Stops checked every 1 min |
| Dhan primary, AngelOne backup | ✅ |
| Redis | ✅ Now adopted, locally on the trading server (latest state + pub/sub) |
| TimescaleDB / QuestDB | ⚠️ Postgres partitioned tables + Parquet instead (simpler with Supabase) |
| Greeks, max pain, PCR momentum, OI unwinding | ✅ M4 |
| Order blocks (SMC) | ⚠️ Test feature only; shift by swing length (look-ahead trap) |
| HMM regimes | ✅ Filtered probabilities only (look-ahead trap) |
| LightGBM strike-breach model | ✅ L1 touch model |
| Delta-neutral hedging, TFT / US models | ❌ Not used |
| Telegram / voice alerts | ✅ M11 |

---

## 11. Architecture review: gaps vs the goal and vs industry practice

Review date 2026-10-24. Professional option-selling desks (volatility funds, prop desks)
differ from our v2 design in the points below. Each gap is now a `TODO.md` task.

### Gaps that matter most for making money

| # | Gap | Industry practice | Why it matters for our goal | Fix |
|---|---|---|---|---|
| G1 | **No pre-agreed go / no-go bar for the backtest** | Success criteria fixed **before** looking at results | Without it, we keep tweaking until something looks good (overfitting) | Owner sets the bar now (see §12) |
| G2 | **Strike IV taken one strike at a time** | Fit a **volatility surface** (SVI / smooth smile) and price strikes from it | Our 0.08–0.12 delta strikes are the thinnest quotes; one bad quote shifts delta and the strike choice | Surface fit in M4 analytics; delta from the surface |
| G3 | **Risk = max loss only** | **Scenario / stress grid**: re-price the book for spot ±1–8%, IV +5 / +10 / +20 points, one day passing; SPAN-like margin view | Max loss says nothing about how fast losses come, or the margin call when IV spikes | Stress grid module; entry blocked if worst case breaks budget |
| G4 | **Only a delta limit** | Limits on **vega and gamma** too | Short options lose most from IV spikes (vega) and fast moves near expiry (gamma) | Added to `RULES.md` §6 |
| G5 | **No liquidity filter** | Min OI / volume, max bid-ask spread per leg | Thin strikes fill badly, and exits in a crash are much worse | Added to `RULES.md` §3 |
| G6 | **No P&L attribution** | Daily P&L split into theta, delta, gamma, vega, costs | Tells us *why* we made or lost money, which is the fastest way to improve decisions | Attribution in journal + UI |
| G7 | **No margin model** | Broker margin calculator / SPAN estimate before each trade | Sizing and the 60% cap need the real margin, not a guess | Groww / Dhan margin API, or SPAN-file estimate |
| G8 | **No strategy decay check** | Halt when live results fall below the backtest's expected range | Edges fade; detect it early instead of after a bad year | `RULES.md` §6b |
| G9 | **Backtest statistics too simple** | Deflated Sharpe ratio, probability of backtest overfitting (CSCV), bootstrap confidence intervals | We will test many parameter sets; luck looks like skill | Add to backtest report |
| G10 | **Historical bid/ask probably missing** | Model spreads conservatively when quotes are missing | Far-OTM premium is small; spread + costs can be 20–40% of it | Conservative spread model by moneyness / time; check against live data |

### Gaps in reliability and operations

| # | Gap | Fix |
|---|---|---|
| G11 | **No backup way to cut risk if Groww is down** | Emergency hedge cash at Dhan (`RULES.md` §7) + runbook |
| G12 | **No runbooks** | One page per failure: feed down at 10:00, Groww down, Dhan login failed, Supabase down, wrong ledger |
| G13 | **No experiment tracking / data versioning** | MLflow (or a simple run table): every backtest and model run saved with data hash, params, results |
| G14 | **No backups / restore test** | Supabase point-in-time recovery + monthly restore test; Parquet copies in a second store |
| G15 | **Job scheduling not defined** | APScheduler inside the service (simple) with missed-run alerts; move to Dagster / Prefect only if pipelines grow |

### What industry uses (and what fits us)

| Area | Industry / pro tools | Our choice |
|---|---|---|
| Event-driven backtest + live with the same code | **NautilusTrader** (production-grade, Python API, backtest-live parity), QuantConnect LEAN | **2-hour spike** before building our own replay engine (T4.0). Use it if its options support and a custom Dhan data adapter are practical; otherwise our minute-bar replay engine |
| Retail option tools in India | Sensibull, Opstra, AlgoTest (backtesting) | Use AlgoTest / Opstra to **sanity-check** our backtest numbers on a few strategies |
| Pricing / vol surface | QuantLib, py_vollib, SVI fits | py_vollib + our SVI fit; QuantLib to cross-check |
| Historical tick data (India) | NSE-authorized vendors (e.g. TrueData, Global Datafeeds) | Decided in T1.1 |
| Risk | Scenario grids, SPAN | Stress grid + margin estimate |
| Research tracking | MLflow, Weights & Biases | MLflow (self-hosted) or a run table |
| Monitoring | Grafana / Prometheus, Sentry, uptime checks | Sentry + Better Stack (or similar) + our health page |

### Honest overall verdict

- **The safety design is strong** (guardrails, fail-closed, watchdog, journal, tests).
- **The weak spot is the money-making core**, not the infrastructure. The edge comes from
  four things: (1) choosing when **not** to trade, (2) correct strike pricing on thin
  quotes, (3) stress-based sizing, (4) cutting losers early. G1–G10 strengthen exactly these.
- **Risk of over-building:** 13 modules + news + ML + RL is a lot for one trade a day. The
  build order already puts the **backtest first**. Hold to it: if the rules-only backtest
  can't clear the §12 bar after costs, adding ML or news will not rescue it, and we change
  the strategy before building more infrastructure.
- **Simplify the first live version:** Redis, the news LLM and RL can wait. A single
  Python service on Railway with in-process state is enough for paper trading.

## 12. Go / no-go bar for the backtest (accepted by owner, 2026-10-24)

Proposed: the rules-only strategy goes forward to paper trading only if, **after all costs**,
in walk-forward tests across all years:

| Metric | Proposed bar |
|---|---|
| Yearly return | ≥ 12% in most years, never below 0% |
| Max drawdown | ≤ 5% in every year |
| Worst month | ≥ −3% |
| Number of trades | ≥ 100 in total (enough to trust) |
| Deflated Sharpe ratio | Positive at 95% confidence |
| Beats "always iron condor" and holding cash | Yes |

## 10. Open questions for the owner

1. **News source:** Tier 1 official sources + one paid API after a 2-week trial (proposed).
2. **Hedge width:** fixed at 200 pts as you described, or let the backtest test 100 / 150 / 200?
3. **Server:** Railway for the backend (decided). Orders are manual for now, so no static
   IP / relay yet.
5. **Multi-user:** decided **personal use only**. `SCALING.md` is kept for reference only.
6. **To verify:** Dhan TOTP login for data APIs; Groww read-only trade book API.
4. **Historical data** for the backtester: which source (still open)?
