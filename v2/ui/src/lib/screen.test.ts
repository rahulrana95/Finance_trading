import { describe, expect, it } from 'vitest'
import { MOCK_SCREEN } from '../api/mock/data'
import type { ScreenRow } from '../api/types'
import { columnValue, countBy, demergerNote, oddsFor, ownRecord, ownShare, pickRows } from './screen'

const row = (patch: Partial<ScreenRow>): ScreenRow => ({ ...MOCK_SCREEN.rows[1]!, ...patch })

describe('screen helpers', () => {
  it('picks the odds for the fall size in the current market state', () => {
    expect(oddsFor(MOCK_SCREEN, 25)?.higherAfter6mPct).toBe(55.8)
    expect(oddsFor({ ...MOCK_SCREEN, market: 'deep' }, 25)?.higherAfter6mPct).toBe(85)
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
  it('filters by fall size and search words', () => {
    const rows = MOCK_SCREEN.rows
    expect(pickRows(rows, 20, '')).toHaveLength(5)
    expect(pickRows(rows, 40, '')).toHaveLength(4)
    expect(pickRows(rows, 20, '  chem ').map((r) => r.symbol)).toEqual(['PIIND'])
    expect(pickRows(rows, 20, 'swiggy')).toHaveLength(1)
  })
  it('gives each column a value to sort by', () => {
    const r = row({ confidence: 'high', belowPct: 30, lastPrice: 12.5, ownHigherAfterYear: 1, ownFallsWithYear: 2 })
    expect(columnValue(r, 'confidence')).toBe(3030)
    expect(columnValue(row({ confidence: 'medium', belowPct: 60 }), 'confidence')).toBe(2060)
    expect(columnValue(r, 'name')).toBe('KPIT Technologies')
    expect(columnValue(r, 'industry')).toBe('Information Technology')
    expect(columnValue(r, 'price')).toBe(12.5)
    expect(columnValue(r, 'below')).toBe(30)
    expect(columnValue(r, 'record')).toBe(0.5)
  })
  it('counts stocks at each confidence', () => {
    expect(countBy(MOCK_SCREEN.rows, 'low')).toBe(5)
    expect(countBy(MOCK_SCREEN.rows, 'high')).toBe(0)
  })
})
