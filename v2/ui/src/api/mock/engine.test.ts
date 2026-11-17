import { describe, expect, it } from 'vitest'
import { belowHighPct, buildPlan, evidence, financialScore, levelPrice, mockCharges, stabilityScore, zone, type PlanInput } from './engine'
import type { FinYear } from '../types'

const full = { falls10: 11, recovered12mPct: 90, longestRecoveryDays: 252, openFallDays: 0, maxDrawdownPct: -30, historyYears: 8 }
const years = (profit: Array<number | null>, revenue: Array<number | null> = [1, 2, 3, 4, 5]): FinYear[] =>
  profit.map((p, i) => ({ period: `FY${2022 + i}`, revenue: revenue[i] ?? null, netProfit: p }))

describe('stability score', () => {
  it('gives full marks when every part is at its best (F10)', () => expect(stabilityScore(full)).toEqual({ score: 100, needs: [] }))
  it('gives no quick-recovery marks at 50% (F11) and half at 70% (F12)', () => {
    expect(stabilityScore({ ...full, recovered12mPct: 50 }).score).toBe(65)
    expect(stabilityScore({ ...full, recovered12mPct: 70 }).score).toBe(83)
  })
  it('caps recovery parts and asks for data with fewer than 5 falls (F13)', () => {
    const r = stabilityScore({ ...full, falls10: 3 })
    expect(r.score).toBe(73)
    expect(r.needs).toContain('Few past falls to judge recovery')
  })
  it('gives no marks for an open fall older than 126 days (F14)', () => expect(stabilityScore({ ...full, openFallDays: 200 }).score).toBe(85))
  it('asks for more history under 8 years', () => expect(stabilityScore({ ...full, historyYears: 5 }).needs).toContain('Fewer than 8 years of price history'))
  it('never leaves the 0 to 100 range', () => {
    const worst = stabilityScore({ falls10: 9, recovered12mPct: 0, longestRecoveryDays: 2000, openFallDays: 900, maxDrawdownPct: -95, historyYears: 1 })
    expect(worst.score).toBe(0)
  })
})

describe('financial score', () => {
  const good = { financials: years([1, 2, 3, 4, 5]), debtToEquity: 0.2, promoterPledgePct: 0, isLender: false }
  it('scores 100 for five rising years, low debt and no pledge (F01)', () => expect(financialScore(good)).toEqual({ score: 100, needs: [] }))
  it('fails "profit every year" on one loss (F02)', () => expect(financialScore({ ...good, financials: years([-1, 2, 3, 4, 5]) }).score).toBe(75))
  it('fails revenue growth when revenue is lower than 4 years ago (F03)', () =>
    expect(financialScore({ ...good, financials: years([1, 2, 3, 4, 5], [9, 2, 3, 4, 5]) }).score).toBe(80))
  it('fails debt at exactly 1.0 (F04)', () => expect(financialScore({ ...good, debtToEquity: 1 }).score).toBe(80))
  it('skips debt for a lender and rescales (F05)', () => expect(financialScore({ ...good, debtToEquity: null, isLender: true })).toEqual({ score: 100, needs: [] }))
  it('fails on any pledge (F06)', () => expect(financialScore({ ...good, promoterPledgePct: 0.1 }).score).toBe(85))
  it('names the missing years (F07)', () => {
    const r = financialScore({ ...good, financials: years([1, null, null, 4, 5]) })
    expect(r.needs).toContain('Net profit for FY2023, FY2024')
    expect(r.score).toBe(75)
  })
  it('scores 0 and lists everything with no data (F08)', () => {
    const r = financialScore({ financials: [], debtToEquity: null, promoterPledgePct: null, isLender: false })
    expect(r.score).toBe(0)
    expect(r.needs).toEqual(expect.arrayContaining(['Five years of revenue', 'Five years of net profit', 'Debt and equity', 'Promoter pledge']))
  })
  it('cannot judge growth when the first or latest year is missing', () => {
    expect(financialScore({ ...good, financials: years([1, 2, 3, 4, 5], [null, 2, 3, 4, 5]) }).score).toBe(80)
    expect(financialScore({ ...good, financials: years([null, 2, 3, 4, 5]) }).score).toBe(55)
    expect(financialScore({ ...good, financials: years([1, 2, 3, 4, null]) }).score).toBe(55)
  })
  it('names missing revenue years', () =>
    expect(financialScore({ ...good, financials: years([1, 2, 3, 4, 5], [1, null, 3, 4, 5]) }).needs).toContain('Revenue for FY2023'))
})

describe('evidence score', () => {
  it('weights the three parts 0.5, 0.3, 0.2 (F15) and takes 20 off per data problem (F16)', () =>
    expect(evidence(80, 60, 2)).toEqual({ stability: 80, financial: 60, dataQuality: 60, evidence: 70 }))
  it('never lets data quality go below zero (F17)', () => expect(evidence(100, 100, 9).dataQuality).toBe(0))
})

describe('zones and levels', () => {
  const levels = [10, 20, 30]
  it('finds the zone at each boundary (Z01 to Z04)', () => {
    expect([9.9, 10, 25, 35].map((b) => zone(b, levels))).toEqual([0, 1, 2, 3])
  })
  it('treats a price above the high as zero below (Z05)', () => expect(belowHighPct(110, 100)).toBe(0))
  it('computes distance below the high', () => expect(belowHighPct(1297.8, 1540)).toBe(15.73))
  it('prices the levels for a high of 1,598.10 (Z06)', () =>
    expect([10, 20, 30, 40].map((p) => levelPrice(1598.1, p))).toEqual([1438.29, 1278.48, 1118.67, 958.86]))
})

describe('plan', () => {
  const base: PlanInput = {
    referenceHigh: 1000, lastPrice: 880, belowPct: 12, capital: 2000000, perStockCapPct: 20, approvedCount: 5,
    levels: [10, 20, 30], parts: [1, 2, 3], lotSize: null, futuresFromStep: 3, filledSteps: [],
  }
  it('allocates the smaller of the cap and an equal share (P01)', () => {
    expect(buildPlan(base).allocation).toBe(400000)
    expect(buildPlan({ ...base, approvedCount: 10 }).allocation).toBe(200000)
    expect(buildPlan({ ...base, approvedCount: 0 }).allocation).toBe(400000)
  })
  it('splits the allocation 1 : 2 : 3 (P02)', () => expect(buildPlan(base).steps.map((s) => s.amount)).toEqual([66666, 133333, 200000]))
  it('offers only reached steps (P03, P04) and skips filled ones (P05, P06)', () => {
    const reached = (b: number, filled: number[] = []) =>
      buildPlan({ ...base, belowPct: b, filledSteps: filled }).steps.filter((s) => s.reached && !s.filled).map((s) => s.step)
    expect(reached(12)).toEqual([1])
    expect(reached(22)).toEqual([1, 2])
    expect(reached(22, [1])).toEqual([2])
    expect(reached(35, [1, 2, 3])).toEqual([])
  })
  it('buys whole shares within the step amount (P07)', () => {
    const step = buildPlan(base).steps[0]!
    expect(step.quantity).toBe(75)
    expect(step.quantity * base.lastPrice).toBeLessThanOrEqual(step.amount)
  })
  it('uses a futures lot on step 3 when one lot fits: combo (P09)', () => {
    const plan = buildPlan({ ...base, belowPct: 35, lastPrice: 650, lotSize: 300 })
    expect(plan.steps.map((s) => s.instrument)).toEqual(['cash', 'cash', 'future'])
    expect(plan.instrumentType).toBe('combo')
    expect(plan.futuresNote).toBe('Step 3 uses one futures lot.')
  })
  it('falls back to shares when a lot is larger than the step (P10)', () => {
    const plan = buildPlan({ ...base, belowPct: 35, lastPrice: 650, lotSize: 700 })
    expect(plan.instrumentType).toBe('cash')
    expect(plan.futuresNote).toContain('more than the 2,00,000')
  })
  it('says lot size needs data when it is unknown (P11)', () => expect(buildPlan(base).futuresNote).toBe('Futures not offered: lot size needs data.'))
  it('is all futures when allowed from step 1 and every lot fits (P12)', () => {
    const plan = buildPlan({ ...base, futuresFromStep: 1, lastPrice: 100, lotSize: 100, belowPct: 35, referenceHigh: 160 })
    expect(plan.instrumentType).toBe('future')
  })
  it('explains when futures are not considered at all', () =>
    expect(buildPlan({ ...base, futuresFromStep: 4 }).futuresNote).toBe('Futures are only considered from step 4.'))
  it('charges 0.12% in the mock', () => expect(mockCharges(50000)).toBe(60))
})
