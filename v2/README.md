# v2: stock screener and dip-buying assistant

**Status: design drafted, waiting for owner approval. No application code yet.**

A small personal app: a table of stable, recovering stocks, buy-zone recommendations
(shares, futures or both), paper trading against real prices, and open trades with profit
or loss. One Python service on Railway serving a React single-page app; Supabase for the
database and sign-in.

| Document | Contents |
|---|---|
| `docs/PRD.md` | What it does, user stories with acceptance criteria, owner decisions needed |
| `docs/ARCHITECTURE.md` | Components, repository layout, data flow, modes, security |
| `docs/DESIGN.md` | Definitions, data model, formulas, services, API, build order |
| `docs/TEST_PLAN.md` | The 148 test cases to be written first |

The research behind the rules is in `../research/2026-11-market-moves/`.
`../AGENTS.md` remains the highest authority; see PRD section 8 for the decisions that
only the owner can make.
