// Pure helpers for the Screener page.
import type { Odds, Screen, ScreenRow } from '../api/types'
import { DEMERGER_DROP_PCT } from '../constants'

export type ScreenSort = 'deepest' | 'record' | 'name'

/** The odds row for a fall of this size in today's market state. */
export const oddsFor = (screen: Screen, level: number): Odds | undefined =>
  screen.odds.find((o) => o.level === level && o.marketDown === screen.marketDown)

/** Share of the stock's own past falls that ended higher a year later, or -1 when it has none. */
export const ownShare = (row: ScreenRow): number => (row.ownFallsWithYear ? row.ownHigherAfterYear / row.ownFallsWithYear : -1)

export const ownRecord = (row: ScreenRow): string =>
  row.ownFallsWithYear ? `${row.ownHigherAfterYear} of ${row.ownFallsWithYear} higher after a year` : 'No earlier fall to judge'

/** A very large one-day drop usually means a demerger or split, not a real fall. */
export const demergerNote = (row: ScreenRow): string | undefined =>
  row.worstDayPct >= DEMERGER_DROP_PCT ? `Fell ${row.worstDayPct.toFixed(0)}% in one day: check for a demerger or split` : undefined

export function pickRows(rows: ScreenRow[], minLevel: number, search: string, sort: ScreenSort): ScreenRow[] {
  const words = search.trim().toLowerCase()
  const kept = rows.filter((r) => r.level >= minLevel && (!words || `${r.name} ${r.symbol} ${r.industry}`.toLowerCase().includes(words)))
  return [...kept].sort((a, b) =>
    sort === 'name' ? a.name.localeCompare(b.name) : sort === 'record' ? ownShare(b) - ownShare(a) || b.belowPct - a.belowPct : b.belowPct - a.belowPct,
  )
}
