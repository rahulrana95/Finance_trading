// Mock-only copy of the rules in v2/docs/DESIGN.md section 3, so the interface can run
// before the backend exists. The backend's Python core is the real implementation.
import type { FinYear, Instrument, InstrumentType, PlanStep, Scores } from '../types'

const clamp = (x: number, lo = 0, hi = 100): number => Math.min(hi, Math.max(lo, x))
/** Linear marks: 0 at `zeroAt`, full at `fullAt` (works in either direction). */
const linear = (x: number, zeroAt: number, fullAt: number): number =>
  clamp(((x - zeroAt) / (fullAt - zeroAt)) * 100) / 100
export const round2 = (x: number): number => Math.round(x * 100) / 100

export interface StabilityInput {
  falls10: number
  recovered12mPct: number
  longestRecoveryDays: number
  openFallDays: number
  maxDrawdownPct: number
  historyYears: number
}

export function stabilityScore(m: StabilityInput): { score: number; needs: string[] } {
  const needs: string[] = []
  let quick = 35 * linear(m.recovered12mPct, 50, 90)
  let noLong = 20 * linear(m.longestRecoveryDays, 756, 252)
  if (m.falls10 < 5) {
    quick = Math.min(quick, 17.5)
    noLong = Math.min(noLong, 10)
    needs.push('Few past falls to judge recovery')
  }
  const nothingOpen = m.openFallDays > 126 ? 0 : 15
  const shallow = 15 * linear(Math.abs(m.maxDrawdownPct), 70, 30)
  const history = 15 * linear(m.historyYears, 3, 8)
  if (m.historyYears < 8) needs.push('Fewer than 8 years of price history')
  return { score: Math.round(quick + noLong + nothingOpen + shallow + history), needs }
}

export interface FinancialInput {
  financials: FinYear[]
  debtToEquity: number | null
  promoterPledgePct: number | null
  isLender: boolean
}

export function financialScore(f: FinancialInput): { score: number; needs: string[] } {
  const needs: string[] = []
  const years = f.financials
  const first = years[0]
  const last = years[years.length - 1]
  const missing = (key: 'revenue' | 'netProfit'): string[] =>
    years.filter((y) => y[key] === null).map((y) => y.period)
  let earned = 0
  let possible = 0
  const check = (weight: number, pass: boolean | null, need: string): void => {
    possible += weight
    if (pass === null) needs.push(need)
    else if (pass) earned += weight
  }
  const enough = years.length >= 5
  const revMissing = missing('revenue')
  const profMissing = missing('netProfit')
  check(
    20,
    !enough || first?.revenue == null || last?.revenue == null ? null : last.revenue > first.revenue,
    revMissing.length ? `Revenue for ${revMissing.join(', ')}` : 'Five years of revenue',
  )
  check(
    25,
    !enough || profMissing.length ? null : years.every((y) => (y.netProfit ?? 0) > 0),
    profMissing.length ? `Net profit for ${profMissing.join(', ')}` : 'Five years of net profit',
  )
  check(
    20,
    !enough || first?.netProfit == null || last?.netProfit == null ? null : last.netProfit > first.netProfit,
    'Net profit for the first and latest year',
  )
  if (!f.isLender) check(20, f.debtToEquity === null ? null : f.debtToEquity < 1, 'Debt and equity')
  check(15, f.promoterPledgePct === null ? null : f.promoterPledgePct === 0, 'Promoter pledge')
  // A missing middle year does not block the growth check, but the owner should still see it.
  if (revMissing.length) needs.push(`Revenue for ${revMissing.join(', ')}`)
  return { score: Math.round((earned / possible) * 100), needs: [...new Set(needs)] }
}

export function evidence(stability: number, financial: number, problems: number): Scores {
  const dataQuality = clamp(100 - 20 * problems)
  return {
    stability,
    financial,
    dataQuality,
    evidence: Math.round(0.5 * stability + 0.3 * financial + 0.2 * dataQuality),
  }
}

export const belowHighPct = (price: number, referenceHigh: number): number =>
  price >= referenceHigh ? 0 : round2((1 - price / referenceHigh) * 100)

/** 0 = not in a buy zone, otherwise the deepest level reached (1-based). */
export function zone(belowPct: number, levels: number[]): number {
  let z = 0
  levels.forEach((level, i) => {
    if (belowPct >= level) z = i + 1
  })
  return z
}

export const levelPrice = (referenceHigh: number, pct: number): number => round2(referenceHigh * (1 - pct / 100))

export interface PlanInput {
  referenceHigh: number
  lastPrice: number
  belowPct: number
  capital: number
  perStockCapPct: number
  approvedCount: number
  levels: number[]
  parts: number[]
  lotSize: number | null
  futuresFromStep: number
  filledSteps: number[]
}

export interface Plan {
  allocation: number
  steps: PlanStep[]
  instrumentType: InstrumentType
  futuresNote: string
}

export function buildPlan(p: PlanInput): Plan {
  const allocation = Math.floor(Math.min((p.perStockCapPct / 100) * p.capital, p.capital / Math.max(p.approvedCount, 1)))
  const totalParts = p.parts.reduce((a, b) => a + b, 0)
  const reachedZone = zone(p.belowPct, p.levels)
  let futuresNote = 'Futures are only considered from step ' + p.futuresFromStep + '.'
  const steps: PlanStep[] = p.levels.map((pct, i) => {
    const step = i + 1
    const amount = Math.floor((allocation * (p.parts[i] ?? 0)) / totalParts)
    let instrument: Instrument = 'cash'
    let quantity = Math.floor(amount / p.lastPrice)
    if (step >= p.futuresFromStep) {
      if (p.lotSize === null) futuresNote = 'Futures not offered: lot size needs data.'
      else if (p.lotSize * p.lastPrice > amount)
        futuresNote = `Futures not offered: one lot is worth about ${Math.round(p.lotSize * p.lastPrice).toLocaleString('en-IN')}, more than the ${amount.toLocaleString('en-IN')} for this step.`
      else {
        instrument = 'future'
        quantity = p.lotSize
        futuresNote = 'Step ' + step + ' uses one futures lot.'
      }
    }
    return {
      step,
      levelPct: pct,
      levelPrice: levelPrice(p.referenceHigh, pct),
      amount,
      instrument,
      quantity,
      reached: step <= reachedZone,
      filled: p.filledSteps.includes(step),
    }
  })
  const offered = steps.filter((s) => s.reached && !s.filled)
  const usesFuture = offered.filter((s) => s.instrument === 'future').length
  const instrumentType: InstrumentType = usesFuture === 0 ? 'cash' : usesFuture === offered.length ? 'future' : 'combo'
  return { allocation, steps, instrumentType, futuresNote }
}

/** Mock charges: a flat 0.12% of traded value stands in for the real charge tables. */
export const mockCharges = (value: number): number => round2(value * 0.0012)
