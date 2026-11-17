# v2 Test plan (tests are written first)

**Status: DRAFT, waiting for owner approval.** Date: 2026-11-17.

Method: for every task in `DESIGN.md` section 8, the tests listed here are committed first
and must fail, then the code is written until they pass. Policy from `TESTING.md` applies:
100% line and branch coverage on `core` and `services`, positive, negative and edge cases,
no skipped tests, deterministic clock and data. Each line below is one test case; the ID is
used as the test name suffix.

Tools: pytest, hypothesis (property tests), time-machine (clock), httpx test client,
Vitest and React Testing Library (interface), Playwright (journeys).

## 1. Core: metrics (V2.2)

| ID | Case | Expect |
|---|---|---|
| M01 | Reference high over 126 rising closes | Equals the last close |
| M02 | Reference high when the peak is 130 days old | Uses only the last 126 days |
| M03 | Fewer than 60 closes | Returns "needs data", no number |
| M04 | Close exactly 10% below the high | Counts as a 10% fall (boundary is inclusive) |
| M05 | Close 9.99% below | No fall event |
| M06 | Fall then close back at the old high | Event ends that day; recovery days correct |
| M07 | Fall never recovers | Event open; open days = days since start |
| M08 | Two separate falls | Two events, non-overlapping |
| M09 | A deeper fall inside an open event | Still one event; depth updated |
| M10 | Recovery share with 4 of 5 inside 252 days | 80% |
| M11 | No fall events | Share is "not available", not 0 or 100 |
| M12 | Max drawdown on a known series | Matches hand-calculated value |
| M13 | Flat price series | Drawdown 0, volatility 0, no events |
| M14 | Series with a missing day | Handled as a gap, no error |
| M15 | Non-positive or NaN price | Rejected with a clear error |
| M16 | Property: any series | 0 ≤ drawdown ≤ 100; events never overlap; recovery days ≥ 1 |
| M17 | ICICI Bank golden file 2016 to 2026 | 11 ten-percent falls, 10 back within 12 months (matches the research) |

## 2. Core: financial checks and scores (V2.3)

| ID | Case | Expect |
|---|---|---|
| F01 | Five years of rising revenue and profit, low debt, no pledge | Financial score 100 |
| F02 | One loss-making year in five | "Profit every year" fails; score drops by its weight |
| F03 | Revenue lower than 4 years ago | Revenue check fails |
| F04 | Debt to equity exactly 1.0 | Fails (limit is below 1.0) |
| F05 | Bank or lender | Debt check skipped; weights rescaled to 100 |
| F06 | Promoter pledge 0.1% | Pledge check fails |
| F07 | Missing FY2022 and FY2023 profit | Check scores 0; `needs` names those two years |
| F08 | No financials at all | Score 0; `needs` lists every required field |
| F09 | Negative equity | Debt check fails; flagged |
| F10 | Stability: all parts at full marks | 100 |
| F11 | Stability: recovery share 50% | Quick-recovery part is 0 |
| F12 | Stability: recovery share 70% | Part is half of its weight |
| F13 | Stability: fewer than 5 fall events | Recovery parts capped at half; `needs` says so |
| F14 | Stability: open fall of 200 days | "Nothing open" part is 0 |
| F15 | Evidence score weights | 0.5, 0.3, 0.2 applied; result between 0 and 100 |
| F16 | Data quality: stale price and unofficial source | 60 |
| F17 | Data quality with five problems | 0, never negative |
| F18 | Property: any inputs | All scores within 0 to 100; more missing data never raises a score |

## 3. Core: zones and plan (V2.4)

| ID | Case | Expect |
|---|---|---|
| Z01 | 9.9% below the high | Zone 0 |
| Z02 | Exactly 10% below | Zone 1 |
| Z03 | 25% below | Zone 2 |
| Z04 | 35% below | Zone 3 |
| Z05 | Above the reference high | Zone 0, below-high shown as 0 |
| Z06 | Level prices for a high of 1,598.10 | 1,438.29, 1,278.48, 1,118.67; hard exit 958.86 |
| P01 | Allocation with 5 approved stocks, 20% cap, Rs 20 L | Rs 4,00,000 per stock |
| P02 | Step amounts for parts 1 : 2 : 3 | 1/6, 2/6, 3/6 of the allocation, summing exactly |
| P03 | Zone 1, nothing held | Offers step 1 only |
| P04 | Zone 2 reached with nothing held | Offers steps 1 and 2 |
| P05 | Zone 2, step 1 already filled | Offers step 2 only |
| P06 | All three steps filled | Offers nothing |
| P07 | Share quantity | Floor of amount / price; never exceeds the amount |
| P08 | Step amount smaller than one share | Step skipped with that reason |
| P09 | Step 3, lot value within the step amount, margin fine | Futures; type is combo with steps 1 and 2 in cash |
| P10 | Step 3, lot value above the step amount | Falls back to cash; type cash |
| P11 | Stock not in futures | Cash only |
| P12 | `futures_from_step` set to 1 and every step fits a lot | Type future |
| P13 | Margin cover would fall below the floor | Futures refused, cash offered |
| P14 | Cycle reference high stays frozen while price makes a new 126-day high inside the cycle | Levels unchanged |
| P15 | Price back at the frozen high | Exit recommendation for the whole cycle |
| P16 | Price at or below the hard exit | Exit recommendation; no further entry steps |
| P17 | Property: any price path | Total bought never exceeds the allocation; steps are taken at most once per cycle |

## 4. Core: risk, charges, profit or loss (V2.5)

| ID | Case | Expect |
|---|---|---|
| R01 | Kill switch on, entry order | Rejected: "new orders are stopped" |
| R02 | Kill switch on, exit order | Allowed |
| R03 | Stock status watching or rejected | Rejected |
| R04 | Latest price older than the freshness limit | Rejected: "prices are stale" |
| R05 | Drawdown at the pause limit | Entry rejected; exit allowed |
| R06 | Order would pass the per-stock cap by Rs 1 | Rejected |
| R07 | Order exactly at the cap | Allowed |
| R08 | Real mode while locked | Rejected: "real trading is locked" |
| R09 | Cycle past hard exit | Entry rejected |
| R10 | The check itself raises an error | Treated as rejected (fail closed) |
| C01 | Delivery buy charges on Rs 50,000 | Matches the hand-calculated table |
| C02 | Delivery sell charges | Includes sell-side taxes |
| C03 | Futures buy and sell charges | Uses the futures table |
| C04 | Zero quantity | Zero charges, no error |
| L01 | One buy, price up | Unrealised profit = (last − cost) × quantity |
| L02 | Two buys at different prices | Average cost correct to the paisa |
| L03 | Partial sell | Realised on the sold part; average cost of the rest unchanged |
| L04 | Full sell | Position closed; unrealised 0 |
| L05 | Charges | Reduce realised profit; shown separately |
| L06 | Paper and real fills for the same stock | Kept in separate positions; filters never mix them |
| L07 | Sell more than held | Rejected |
| L08 | Property: any sequence of fills | Realised + unrealised + charges equals cash flow plus market value |

## 5. Adapters and database (V2.6, V2.7)

| ID | Case | Expect |
|---|---|---|
| D01 | Migrations on an empty database | All tables created; downgrade works |
| D02 | Insert duplicate (`symbol`, `date`) price | Rejected by the unique rule |
| D03 | Update or delete a row in `run_steps`, `orders`, `fills` | Refused |
| D04 | Seed data | Twelve stocks with the statuses in the PRD |
| A01 | Price adapter parses a recorded response | Correct bars, dates in India time |
| A02 | Price adapter: network error, then success | One retry, then data |
| A03 | Price adapter: two failures | Raises a typed error; no partial write |
| A04 | Price adapter: malformed or empty response | Typed error |
| A05 | Financials file with valid rows | Stored with source and date |
| A06 | Financials file with a bad row | That row rejected with the reason; good rows kept |
| A07 | Financials file with a negative revenue or unknown period | Rejected |
| A08 | Real broker stub, any order | Raises "real trading is locked"; makes no network call |

## 6. Services (V2.8 to V2.10)

| ID | Case | Expect |
|---|---|---|
| S01 | Screener on three stocks | Metrics written for each; run log has one summary line per stock |
| S02 | Screener when one stock's fetch fails | Other two updated; failed one marked "needs data" |
| S03 | Screener run twice on the same day | No duplicate price rows; metrics replaced |
| S04 | A stock's score falls below the approval bar | Flagged for review; status not changed automatically |
| G01 | Algo run, no stock in a zone | No recommendations; steps say "nothing to do" per stock |
| G02 | Algo run, one approved stock in zone 1 | One entry recommendation with plan, reasons, risk result |
| G03 | Stock in zone but status watching | No recommendation |
| G04 | Stale prices | Run ends at pre-check; no recommendations |
| G05 | Kill switch on | Exit recommendations only |
| G06 | Same slot run twice | No duplicate recommendation |
| G07 | Dry run | Steps written; no recommendations, no orders |
| G08 | Open position reaches target | Exit recommendation created |
| G09 | Recommendation no longer valid (price left the zone before approval) | Marked expired |
| G10 | Run steps | Ordered by sequence, each with time, subject, level, message |
| T01 | Approve as paper | Order created, filled at the next fresh price with slippage, fill logged with source |
| T02 | Approve as real | 409 "locked"; no order row |
| T03 | Approve when risk now fails (price moved) | Rejected with the reason; recommendation stays new |
| T04 | Approve twice | Second call rejected; one order only |
| T05 | Paper order with no fresh price | Stays open; fills on the next run |
| T06 | Price worse than the limit | Does not fill |
| T07 | Skip with a note | Status skipped; note stored |
| T08 | Exit approved | Sells the whole cycle; cycle closed with the reason |
| O01 | Open trades, mode paper | Only paper positions |
| O02 | Open trades, mode all | Paper and real shown with a mode label, never summed together |
| O03 | Profit or loss totals | Equal the sum of the log to the paisa |

## 7. API and auth (V2.8 to V2.11)

| ID | Case | Expect |
|---|---|---|
| H01 | `GET /api/health` without a session | 200 |
| H02 | Any other route without a session | 401 |
| H03 | Valid token for a different email | 403 |
| H04 | Expired or tampered token | 401 |
| H05 | Stocks list with status, zone, score filters and sort | Correct rows and order |
| H06 | Unknown symbol | 404 |
| H07 | Invalid filter value | 422 with a readable message |
| H08 | Recommendations filtered by type, zone, score, status together | Correct rows |
| H09 | Approve with mode missing or unknown | 422 |
| H10 | Settings change outside allowed ranges | 422; nothing saved |
| H11 | Kill switch on through settings | Next run produces no entry recommendation |
| H12 | Response shapes | Match the published schema (contract test) |

## 8. Interface (V2.12, V2.13)

| ID | Case | Expect |
|---|---|---|
| U01 | Sign-in with empty fields | Field messages; no request sent |
| U02 | Wrong password | One generic error; password field cleared |
| U03 | Successful sign-in | Lands on Stocks; session kept on reload |
| U04 | Stocks table | Renders rows, sorts by score, filters by status |
| U05 | Stock with missing data | "Needs data" list visible with each item |
| U06 | Ideas card | Shows type, plan steps, amounts, evidence parts |
| U07 | Paper or real choice | Paper selected by default; real shows the locked reason and disables approve |
| U08 | Approve | Button disables while sending; card moves to approved; error shown on failure |
| U09 | Trades page filter | Switching paper / real / all changes rows and totals |
| U10 | Profit and loss colours | Also carry a sign and arrow (not colour alone) |
| U11 | Algo runs | Steps in order; "Run now" adds a new run at the top |
| U12 | Loading, empty and error states on every page | Each renders |
| U13 | Keyboard only | Every control reachable and labelled |

## 9. End-to-end journeys

| ID | Journey | Expect |
|---|---|---|
| E01 | Sign in, open Stocks, run the screener | Table refreshes; run appears in Algo runs |
| E02 | Seeded stock in zone 1: run now, open Ideas, approve as paper | Order filled; position in Trades; profit or loss updates after a price change |
| E03 | Price reaches the target | Exit idea appears; approving closes the cycle; realised profit shown |
| E04 | Kill switch on | No new entry ideas; exits still offered |
| E05 | Upload financials for a stock with missing data | "Needs data" clears; evidence score rises |
| E06 | Try a real trade | Blocked with the locked message; nothing in the log |

## 10. Counts

148 test cases: 17 metrics, 18 scores, 23 zones and plan, 22 risk, charges and profit or
loss, 12 adapters and database, 25 services, 12 API, 13 interface, 6 journeys.
