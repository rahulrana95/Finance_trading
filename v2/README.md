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

## Code rules for v2 (owner, 2026-11-17)

These add to `../ENGINEERING.md` and `../TESTING.md`:

- **Small modules.** One job per file; split before a file gets long.
- **Standard packages first.** Settings, middleware, static files, validation and similar
  come from well-known libraries (pydantic-settings, Starlette middleware and StaticFiles,
  asgi-correlation-id). Write our own only when nothing suitable exists.
- **Constants in one place.** `backend/src/steady/constants.py`; the interface keeps its own
  in one file too. No repeated literals.
- **No repetition.** Shared helpers and middleware instead of copy-paste.
- **100% unit tests** (`tests/unit`) and **100% route-level tests** (`tests/integration`,
  through the real app). Coverage is enforced at 100% line and branch.
