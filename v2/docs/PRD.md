# v2 PRD: Stock screener and dip-buying assistant (small first build)

**Status: DRAFT, waiting for owner approval. Nothing in `v2/` is built yet.**
Date: 2026-11-17. Related: `ARCHITECTURE.md`, `DESIGN.md`, `TEST_PLAN.md` in this folder.

## 1. Problem

The owner wants one personal app that:

1. keeps a table of large Indian stocks that have reliably recovered from falls and have
   sound businesses,
2. tells him when one of them is in a buy zone, and whether to buy shares, futures or both,
3. lets him place that as a paper trade (default) or a real trade,
4. logs every trade against real market prices, and
5. shows open trades and profit or loss, filtered by paper or real.

The research behind the rules is in `research/2026-11-market-moves/` and
`BACKTEST_RESULTS.md`. Two findings shape this build:

- Past recovery did not predict future recovery (rank correlation about -0.13 between
  halves), so the screener is a filter plus a business check, never a promise.
- Uncapped averaging down and frequent re-tuning both lost money. The rules here are fixed
  and capped.

## 2. Goals for this build

| # | Goal | Measure |
|---|---|---|
| G1 | Sign in with email and password | Only the owner's account can open any screen or API |
| G2 | Stock table with stability and financial checks | Every row shows its scores, what data is missing, and when it was last refreshed |
| G3 | Buy-zone detection | A stock at or below a buy level appears as a recommendation within one run |
| G4 | Recommendation of cash, future or combo, with a stepped plan | Each recommendation states instrument, amounts per step and the reason |
| G5 | Paper trading against real prices | Paper orders fill from fetched market prices, with charges, and are logged |
| G6 | Open trades and profit or loss, with a paper / real filter | Totals match the trade log to the rupee |
| G7 | Run on a schedule and on demand, with readable reasoning | Each run stores a step-by-step log shown in the app |

## 3. Not in this build

- Sending real orders to a broker. The real mode exists in the data model and the interface,
  but stays locked (see section 8).
- Machine-learning confidence. This build shows an evidence score built from measured
  parts. A learned, calibrated confidence comes later, once enough ideas have outcomes.
- Options strategies, multiple users, a phone app, tax reports.
- Automatic approval of orders. The owner approves every order.

## 4. User and principles

One user, the account owner. Design principles: plain words, one main action per screen,
anything needing attention at the top, every number traceable to its source, and "I don't
know" shown as "needs data" instead of a guess.

## 5. Scope: stocks

Starting watchlist (from the research shortlist):

| Group | Stocks |
|---|---|
| Approved to trade on paper | ICICI Bank, Nestle India, Pidilite, Titan, Marico |
| Watching, not approved | Torrent Pharma, Phoenix Mills, Indian Hotels, KEI Industries |
| Rejected by the research, kept for reference | Coforge, Solar Industries, Navin Fluorine |

The screener can add candidates from the Nifty 500 list; only the owner can approve one.

## 6. User stories and acceptance criteria

### S1 Sign in
- As the owner I sign in with email and password.
- **Accept:** wrong password shows one generic error; five failures lock sign-in for 15
  minutes; any API call without a valid session returns 401; sign-out ends the session.

### S2 See the stock table
- As the owner I see each stock's status, price, distance below its 6-month high, stability
  score, financial check, evidence score, and "needs data" notes.
- **Accept:** table sorts and filters by status, zone and score; each score opens its parts;
  a stock with missing financials shows exactly which fields are missing.

### S3 Refresh the screener
- As the owner I press "Run screener" or it runs weekly.
- **Accept:** prices and metrics update; a stock that no longer passes is flagged, not
  silently removed; the run log lists what changed and what could not be fetched.

### S4 Add financial data
- As the owner I upload a results file or type figures for a stock when the app cannot get
  them.
- **Accept:** the financial check and evidence score recompute; the source and date are
  stored; bad rows are rejected with the reason.

### S5 Get a recommendation
- As the owner I see a recommendation when a stock is in a buy zone.
- **Accept:** it states: stock, zone, cash / future / combo, the stepped plan (amounts in
  ratio 1 : 2 : 3 from a minimum start), exit levels, evidence score with its parts, and the
  risk-check result. No recommendation is shown for a stock that is not approved.

### S6 Filter recommendations
- **Accept:** filters for instrument type, zone depth, minimum evidence score, and status
  (new, approved, skipped, expired) combine and are kept in the address bar.

### S7 Place a paper trade
- As the owner I approve a step as a paper trade.
- **Accept:** an order is created; it fills at the next fetched market price with slippage
  and charges applied; the fill, price source and time are logged; nothing leaves the app.

### S8 Real trade is visible but locked
- **Accept:** choosing "Real" shows why it is locked and what unlocks it; the API rejects a
  real order with a clear reason; no broker call is made.

### S9 See open trades and profit or loss
- **Accept:** open positions show quantity, average price, last price, unrealised profit or
  loss and the plan step; a filter switches paper / real / all; totals for realised,
  unrealised and charges match the trade log.

### S10 Watch a run
- As the owner I see the latest run's reasoning line by line and can press "Run now" or
  "Dry run".
- **Accept:** each run stores ordered steps with time, subject, message and level; a dry run
  creates no orders; a failed data fetch stops new recommendations and says so.

### S11 Exits happen by rule
- **Accept:** when price reaches the plan's target, or its hard exit level, the app proposes
  the closing order; on paper it is filled and logged the same way as entries.

## 7. What the app must tell the owner it does not know

For every stock the app lists what it needs to raise the evidence score, for example:
"5 years of revenue and profit", "promoter pledge", "debt", "fewer than 8 years of price
history", "price data older than 1 day". If a source fails, the stock shows "needs data"
and is excluded from new recommendations until fixed.

## 8. Guardrails and owner decisions needed before building

`AGENTS.md` is the highest authority in this repo. Items marked there as locked can only
be changed by the owner in the owner's own commit. This build touches them:

| # | Decision needed from the owner | Why | Default if approved as written |
|---|---|---|---|
| D1 | Allow v2 to track and **paper trade** NSE shares and single-stock futures | `AGENTS.md` section 1 limits the project to Nifty 50 index options | Owner adds a v2 section to `AGENTS.md`; until then v2 runs screener and recommendations only, with paper orders disabled |
| D2 | Real trading stays locked in this build | `AGENTS.md` section 3: paper first, owner turns live on | Locked; unlock needs 8 weeks of paper results and a later decision |
| D3 | Price source for this build | No broker is chosen yet | Daily and delayed prices from a public source behind an interface, clearly labelled; replaced by the broker feed later |
| D4 | Financial data source | No free official API gives 5 years of results | Manual upload or entry per stock, with the source recorded; the app lists what is missing |
| D5 | Sign-in method | Email and password requested | Supabase Auth, one allow-listed email |
| D6 | Paper capital and limits | Needed for sizing | Rs 20 L paper capital, at most 20% per stock, new buys pause at 25% drawdown |
| D7 | Buy levels and plan | From the research | Levels at 10 / 20 / 30% below the 6-month high, parts 1 : 2 : 3, sell at the old high, close at 40% below |

## 9. Success criteria for the build

- All tests in `TEST_PLAN.md` pass, written before the code they test, with 100% line and
  branch coverage for `v2/backend` core and services (`TESTING.md`).
- The owner can sign in, see the table, run the screener, get a recommendation for a stock
  in a buy zone, paper trade it, and see it in open trades with correct profit or loss.
- Every run and every order can be traced in the log.

## 10. Risks

| Risk | Handling |
|---|---|
| Public price source is unofficial and can lag or fail | Labelled in the app; fail closed; replaced by broker data |
| Financial data is incomplete | Shown as "needs data"; lowers the evidence score; never guessed |
| Owner reads the evidence score as a probability | Named "evidence score", with its parts shown; no percentage of success claimed |
| A screened stock collapses | Per-stock cap, hard exit at 40% below, no averaging past step 3 |
| Futures lots are too large for the plan | Futures step is offered only when one lot fits the step and margin limits; otherwise cash only |
