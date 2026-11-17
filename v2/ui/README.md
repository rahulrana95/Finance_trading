# Steady interface (v2/ui)

React and TypeScript single-page app for the v2 stock screener and paper-trading
assistant. **It currently runs on sample data from an in-browser mock; no backend, no
broker, no real orders.**

| Command | Does |
|---|---|
| `pnpm install` | Install packages |
| `pnpm dev` | Run locally with reload |
| `pnpm test` / `pnpm coverage` | Run the tests |
| `pnpm build` | Type-check and build to `dist/` |
| `pnpm start` | Serve the built app on `$PORT` (used for the hosted demo) |

Demo sign-in: `demo@steady.app` / `paper-trading`.

## Layout

| Path | Contents |
|---|---|
| `src/api/types.ts` | The `Api` interface and every data shape the screens use |
| `src/api/index.ts` | The one place that chooses the implementation (mock now, HTTP later) |
| `src/api/mock/` | In-memory mock: seed data, a real price snapshot, and a copy of the rules in `v2/docs/DESIGN.md` |
| `src/pages/` | Sign in, Stocks, Stock detail, Ideas, Trades, Algo runs, Settings |
| `src/components/`, `src/lib/`, `src/auth/` | Shared pieces, formatting, session |
| `src/**/*.test.ts(x)` | Tests, next to the code they cover |

## Moving from mock to the real backend

Each backend route replaces one method of `Api` in `src/api/index.ts`. The screens do not
change, because they only call that interface. The rules in `src/api/mock/engine.ts` are a
stand-in; the Python core is the real implementation and the mock copy is deleted once the
matching route is live.

Prices in `src/api/mock/prices.snapshot.json` are daily closes to 17 Nov 2026 from a
public source. Business figures come from `research/2026-11-market-moves/company_research.md`.
