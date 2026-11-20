import { describe, expect, it } from 'vitest'
import { MOCK_SCREEN } from '../api/mock/data'
import type { ScreenRow } from '../api/types'
import { demergerNote, oddsFor, ownRecord, ownShare, pickRows } from './screen'

const row = (patch: Partial<ScreenRow>): ScreenRow => ({ ...MOCK_SCREEN.rows[1]!, ...patch })

describe('screen helpers', () => {
  it('picks the odds for the fall size in the current market state', () => {
    expect(oddsFor(MOCK_SCREEN, 25)?.higherAfter6mPct).toBe(55.8)
    expect(oddsFor({ ...MOCK_SCREEN, marketDown: true }, 25)?.higherAfter6mPct).toBe(75.5)
    expect(oddsFor(MOCK_SCREEN, 99)).toBeUndefined()
  })
  it("describes a stock's own record, or says there is none", () => {
    expect(ownRecord(row({ ownHigherAfterYear: 5, ownFallsWithYear: 7 }))).toBe('5 of 7 higher after a year')
    expect(ownRecord(row({ ownFallsWithYear: 0 }))).toBe('No earlier fall to judge')
    expect(ownShare(row({ ownHigherAfterYear: 1, ownFallsWithYear: 4 }))).toBe(0.25)
    expect(ownShare(row({ ownFallsWithYear: 0 }))).toBe(-1)
  })
  it('warns only about very large one-day drops', () => {
    expect(demergerNote(row({ worstDayPct: 62 }))).toBe('Fell 62% in one day: check for a demerger or split')
    expect(demergerNote(row({ worstDayPct: 34.9 }))).toBeUndefined()
  })
  it('filters by fall size and search words, and sorts three ways', () => {
    const rows = MOCK_SCREEN.rows
    expect(pickRows(rows, 20, '', 'deepest').map((r) => r.symbol)).toEqual(['VEDL', 'KPITTECH', 'SWIGGY', 'PIIND', 'NESTLEIND'])
    expect(pickRows(rows, 40, '', 'deepest')).toHaveLength(4)
    expect(pickRows(rows, 20, '  chem ', 'deepest').map((r) => r.symbol)).toEqual(['PIIND'])
    expect(pickRows(rows, 20, 'swiggy', 'deepest')).toHaveLength(1)
    expect(pickRows(rows, 20, '', 'name').map((r) => r.symbol)).toEqual(['KPITTECH', 'NESTLEIND', 'PIIND', 'SWIGGY', 'VEDL'])
    expect(pickRows(rows, 20, '', 'record').map((r) => r.symbol)).toEqual(['NESTLEIND', 'KPITTECH', 'PIIND', 'VEDL', 'SWIGGY'])
  })
})
