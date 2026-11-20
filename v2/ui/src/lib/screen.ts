// Pure helpers for the Screener page.
import type { Confidence, Odds, Screen, ScreenRow } from '../api/types'
import { CONFIDENCE_RANK, DEMERGER_DROP_PCT } from '../constants'
import type { SortValue } from './sort'

export type ScreenColumn = 'confidence' | 'name' | 'industry' | 'price' | 'below' | 'record'

/** The odds row for a fall of this size in today's market state. */
export const oddsFor = (screen: Screen, level: number): Odds | undefined => screen.odds.find((o) => o.level === level && o.market === screen.market)

/** Share of the stock's own past falls that ended higher a year later, or -1 when it has none. */
export const ownShare = (row: ScreenRow): number => (row.ownFallsWithYear ? row.ownHigherAfterYear / row.ownFallsWithYear : -1)

export const ownRecord = (row: ScreenRow): string =>
  row.ownFallsWithYear ? `${row.ownHigherAfterYear} of ${row.ownFallsWithYear} higher after a year` : 'No earlier fall to judge'

/** A very large one-day drop usually means a demerger or split, not a real fall. */
export const demergerNote = (row: ScreenRow): string | undefined =>
  row.worstDayPct >= DEMERGER_DROP_PCT ? `Fell ${row.worstDayPct.toFixed(0)}% in one day: check for a demerger or split` : undefined

export function pickRows(rows: ScreenRow[], minLevel: number, search: string): ScreenRow[] {
  const words = search.trim().toLowerCase()
  return rows.filter((r) => r.level >= minLevel && (!words || `${r.name} ${r.symbol} ${r.industry}`.toLowerCase().includes(words)))
}

/** What each column sorts by. Confidence ties are broken by the depth of the fall. */
export function columnValue(row: ScreenRow, column: ScreenColumn): SortValue {
  if (column === 'confidence') return CONFIDENCE_RANK[row.confidence] * 1000 + row.belowPct
  if (column === 'name') return row.name
  if (column === 'industry') return row.industry
  if (column === 'price') return row.lastPrice
  return column === 'below' ? row.belowPct : ownShare(row)
}

export const countBy = (rows: ScreenRow[], confidence: Confidence): number => rows.filter((r) => r.confidence === confidence).length
