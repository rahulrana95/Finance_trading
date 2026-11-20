import {
  ApiError,
  type Api,
  type Mode,
  type ModeFilter,
  type Pnl,
  type Position,
  type RecFilter,
  type Recommendation,
  type Run,
  type RunKind,
  type RunStep,
  type Session,
  type Settings,
  type Stock,
  type StockStatus,
  type TradeLogEntry,
} from '../types'
import { MOCK_DELAY_MS } from '../../constants'
import { DEFAULT_SETTINGS, DEMO_EMAIL, DEMO_PASSWORD, MOCK_NOW, MOCK_SCREEN, SEED_STOCKS, SNAPSHOT, type Snapshot } from './data'
import { belowHighPct, buildPlan, evidence, financialScore, mockCharges, round2, stabilityScore, zone } from './engine'

const clone = <T>(x: T): T => structuredClone(x)
const PRICE_SOURCE = 'Public daily close (snapshot)'

/** The price snapshot for a seeded stock; a seed without one is a build mistake. */
export function snapshotFor(symbol: string, snapshots: Snapshot[] = SNAPSHOT): Snapshot {
  const snap = snapshots.find((s) => s.symbol === symbol)
  if (!snap) throw new Error(`No price snapshot for ${symbol}`)
  return snap
}

/** Latest year's net profit in words, for an idea's reasons. */
export const latestProfit = (financials: Array<{ netProfit: number | null }>): string =>
  financials[financials.length - 1]?.netProfit?.toLocaleString('en-IN') ?? 'not known'

export interface MockOptions {
  delayMs?: number
  now?: () => Date
}

export function createMockApi({ delayMs = MOCK_DELAY_MS, now = () => new Date(MOCK_NOW) }: MockOptions = {}): Api {
  const wait = <T>(value: T): Promise<T> =>
    new Promise((resolve) => (delayMs ? setTimeout(() => resolve(clone(value)), delayMs) : resolve(clone(value))))

  let settings: Settings = clone(DEFAULT_SETTINGS)
  let screen = clone(MOCK_SCREEN)
  let failedSignIns = 0
  let seq = 0
  const id = (prefix: string): string => `${prefix}-${++seq}`

  const stocks: Stock[] = SEED_STOCKS.map((seed) => {
    const snap = snapshotFor(seed.symbol)
    const stability = stabilityScore({
      falls10: snap.falls10,
      recovered12mPct: snap.rec12,
      longestRecoveryDays: snap.longest,
      openFallDays: 0,
      maxDrawdownPct: snap.maxdd,
      historyYears: snap.years,
    })
    const financial = financialScore(seed)
    // Data problems: unofficial price source always counts; missing financial fields count once.
    const problems = 1 + (financial.needs.length ? 1 : 0)
    const needs = [...stability.needs, ...financial.needs, 'Official price feed (currently a public source)']
    if (seed.lotSize === null) needs.push('Futures lot size')
    const below = belowHighPct(snap.last, snap.ref)
    return {
      symbol: seed.symbol,
      name: seed.name,
      industry: seed.industry,
      status: seed.status,
      lastPrice: snap.last,
      priceAsOf: snap.asof,
      referenceHigh: snap.ref,
      belowHighPct: below,
      zone: zone(below, DEFAULT_SETTINGS.levels),
      lotSize: seed.lotSize,
      isLender: seed.isLender,
      falls10: snap.falls10,
      recovered12mPct: snap.rec12,
      longestRecoveryDays: snap.longest,
      maxDrawdownPct: snap.maxdd,
      historyYears: snap.years,
      financials: seed.financials,
      debtToEquity: seed.debtToEquity,
      promoterPledgePct: seed.promoterPledgePct,
      business: seed.business,
      scores: evidence(stability.score, financial.score, problems),
      needs,
      history: snap.hist,
    }
  })

  const recommendations: Recommendation[] = []
  const positions: Position[] = []
  const log: TradeLogEntry[] = []
  const runs: Run[] = []

  const find = (symbol: string): Stock => {
    const stock = stocks.find((s) => s.symbol === symbol)
    if (!stock) throw new ApiError(`Unknown stock ${symbol}`, 'not_found')
    return stock
  }
  const filledSteps = (symbol: string): number[] =>
    recommendations.filter((r) => r.symbol === symbol).flatMap((r) => r.steps.filter((s) => s.filled).map((s) => s.step))

  function recommend(stock: Stock): Recommendation | null {
    const approved = stocks.filter((s) => s.status === 'approved').length
    const plan = buildPlan({
      referenceHigh: stock.referenceHigh,
      lastPrice: stock.lastPrice,
      belowPct: stock.belowHighPct,
      capital: settings.paperCapital,
      perStockCapPct: settings.perStockCapPct,
      approvedCount: approved,
      levels: settings.levels,
      parts: settings.parts,
      lotSize: stock.lotSize,
      futuresFromStep: 3,
      filledSteps: filledSteps(stock.symbol),
    })
    if (!plan.steps.some((s) => s.reached && !s.filled)) return null
    return {
      id: id('rec'),
      symbol: stock.symbol,
      name: stock.name,
      zone: stock.zone,
      instrumentType: plan.instrumentType,
      steps: plan.steps,
      targetPrice: stock.referenceHigh,
      hardExitPrice: round2(stock.referenceHigh * (1 - settings.hardExitPct / 100)),
      evidenceScore: stock.scores.evidence,
      reasons: [
        `${stock.belowHighPct}% below its 6-month high of ${stock.referenceHigh.toLocaleString('en-IN')}.`,
        `Back within a year after ${stock.recovered12mPct}% of its ${stock.falls10} past 10% falls.`,
        `Latest year net profit ${latestProfit(stock.financials)} crore; business rated ${stock.business.durability.toLowerCase()}.`,
      ],
      risks: [stock.business.watch, `Its worst fall since 2016 was ${Math.abs(stock.maxDrawdownPct)}%.`],
      futuresNote: plan.futuresNote,
      status: 'new',
      createdAt: now().toISOString(),
    }
  }

  function run(kind: RunKind): Run {
    const steps: RunStep[] = []
    const at = now().toISOString()
    const add = (subject: string, level: RunStep['level'], message: string): void => {
      steps.push({ seq: steps.length + 1, at, subject, level, message })
    }
    add('Prices', 'ok', `Loaded for ${stocks.length} stocks from the snapshot of ${stocks[0]?.priceAsOf}.`)
    let created = 0
    if (settings.killSwitch) add('Safety', 'warn', 'New orders are stopped. Checking exits only.')
    for (const stock of stocks.filter((s) => s.status === 'approved')) {
      if (stock.zone === 0) {
        add(stock.name, 'info', `${stock.belowHighPct}% below its high. First buy needs ${settings.levels[0]}%. Nothing to do.`)
        continue
      }
      const open = recommendations.find((r) => r.symbol === stock.symbol && r.status === 'new')
      if (open) {
        add(stock.name, 'info', `In buy zone ${stock.zone}. An idea is already waiting for you.`)
      } else if (settings.killSwitch) {
        add(stock.name, 'warn', `In buy zone ${stock.zone}, but new orders are stopped.`)
      } else if (kind === 'dry_run') {
        add(stock.name, 'action', `In buy zone ${stock.zone}. A real run would propose a buy. Dry run: no idea created.`)
      } else {
        const rec = recommend(stock)
        if (rec) {
          recommendations.unshift(rec)
          created += 1
          add(stock.name, 'action', `${stock.belowHighPct}% below its high, in buy zone ${stock.zone}. Proposed a ${rec.instrumentType} buy. ${rec.futuresNote}`)
        } else add(stock.name, 'info', `In buy zone ${stock.zone}. Every step reached is already bought.`)
      }
    }
    const watching = stocks.filter((s) => s.status !== 'approved' && s.zone > 0)
    if (watching.length)
      add('Not approved', 'info', `${watching.map((s) => s.name).join(', ')} ${watching.length === 1 ? 'is' : 'are'} in a buy zone but not approved, so no idea.`)
    const summary = kind === 'dry_run' ? 'Dry run, no orders' : created ? `${created} idea${created === 1 ? '' : 's'} proposed` : 'No action'
    add('Done', 'ok', `${summary}.`)
    const result: Run = { id: id('run'), kind, startedAt: at, summary, steps }
    runs.unshift(result)
    return result
  }

  run('scheduled')

  const byMode = <T extends { mode: Mode }>(rows: T[], mode: ModeFilter): T[] =>
    mode === 'all' ? rows : rows.filter((r) => r.mode === mode)

  return {
    async signIn(email, password): Promise<Session> {
      if (failedSignIns >= 5) throw new ApiError('Too many attempts. Try again in 15 minutes.', 'locked')
      if (email.trim().toLowerCase() !== DEMO_EMAIL || password !== DEMO_PASSWORD) {
        failedSignIns += 1
        throw new ApiError('Email or password is not right.', 'invalid_credentials')
      }
      failedSignIns = 0
      return wait({ email: DEMO_EMAIL })
    },
    listStocks: () => wait(stocks),
    getStock: async (symbol) => wait(find(symbol)),
    async setStockStatus(symbol, status: StockStatus) {
      const stock = find(symbol)
      stock.status = status
      return wait(stock)
    },
    listRecommendations(filter: RecFilter = {}) {
      const rows = recommendations.filter(
        (r) =>
          (!filter.instrumentType || filter.instrumentType === 'any' || r.instrumentType === filter.instrumentType) &&
          (!filter.status || filter.status === 'any' || r.status === filter.status) &&
          r.zone >= (filter.minZone ?? 0) &&
          r.evidenceScore >= (filter.minScore ?? 0),
      )
      return wait(rows)
    },
    async approve(recId, mode) {
      const rec = recommendations.find((r) => r.id === recId)
      if (!rec) throw new ApiError('That idea no longer exists.', 'not_found')
      if (mode === 'real') throw new ApiError('Real trading is locked until the paper period is complete.', 'locked')
      if (settings.killSwitch) throw new ApiError('New orders are stopped. Turn them back on in Settings.', 'kill_switch')
      const step = rec.steps.find((s) => s.reached && !s.filled)
      if (rec.status !== 'new' || !step) throw new ApiError('This idea has already been handled.', 'conflict')
      if (step.quantity < 1) throw new ApiError('This step is smaller than one share.', 'too_small')
      const stock = find(rec.symbol)
      const price = round2(stock.lastPrice * 1.0005)
      const charges = mockCharges(price * step.quantity)
      const at = now().toISOString()
      step.filled = true
      if (!rec.steps.some((s) => s.reached && !s.filled)) rec.status = 'approved'
      const existing = positions.find((p) => p.symbol === rec.symbol && p.mode === mode && p.instrument === step.instrument)
      if (existing) {
        const quantity = existing.quantity + step.quantity
        existing.avgPrice = round2((existing.avgPrice * existing.quantity + price * step.quantity) / quantity)
        existing.quantity = quantity
        existing.charges = round2(existing.charges + charges)
        existing.unrealised = round2((stock.lastPrice - existing.avgPrice) * quantity)
      } else {
        positions.push({
          id: id('pos'), symbol: rec.symbol, name: rec.name, mode, instrument: step.instrument, quantity: step.quantity,
          avgPrice: price, lastPrice: stock.lastPrice, charges, unrealised: round2((stock.lastPrice - price) * step.quantity), openedAt: at,
        })
      }
      log.unshift({ id: id('fill'), at, symbol: rec.symbol, mode, side: 'buy', instrument: step.instrument, quantity: step.quantity, price, charges, source: PRICE_SOURCE })
      return wait(rec)
    },
    async skip(recId) {
      const rec = recommendations.find((r) => r.id === recId)
      if (!rec) throw new ApiError('That idea no longer exists.', 'not_found')
      if (rec.status !== 'new') throw new ApiError('This idea has already been handled.', 'conflict')
      rec.status = 'skipped'
      return wait(rec)
    },
    openTrades: (mode) => wait(byMode(positions, mode)),
    tradeLog: (mode) => wait(byMode(log, mode)),
    pnl(mode): Promise<Pnl> {
      const rows = byMode(positions, mode)
      return wait({
        invested: round2(rows.reduce((a, p) => a + p.avgPrice * p.quantity, 0)),
        unrealised: round2(rows.reduce((a, p) => a + p.unrealised, 0)),
        realised: 0,
        charges: round2(rows.reduce((a, p) => a + p.charges, 0)),
      })
    },
    listRuns: () => wait(runs),
    startRun: async (kind) => wait(run(kind)),
    getScreen: () => wait({ running: false, error: null, screen }),
    async startScreen() {
      screen = { ...screen, id: id('screen'), createdAt: now().toISOString() }
      return wait({ running: false, error: null, screen })
    },
    getSettings: () => wait(settings),
    async updateSettings(patch) {
      if (patch.realLocked === false) throw new ApiError('Real trading cannot be unlocked from the app yet.', 'locked')
      settings = { ...settings, ...patch }
      return wait(settings)
    },
  }
}
