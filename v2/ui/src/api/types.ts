export type StockStatus = 'approved' | 'watching' | 'rejected'
export type Mode = 'paper' | 'real'
export type ModeFilter = Mode | 'all'
export type Instrument = 'cash' | 'future'
export type InstrumentType = 'cash' | 'future' | 'combo'
export type RecStatus = 'new' | 'approved' | 'skipped' | 'expired'
export type RunKind = 'scheduled' | 'on_demand' | 'dry_run' | 'screener'
export type RunStatus = 'running' | 'done' | 'failed'
export type StepLevel = 'ok' | 'info' | 'action' | 'warn' | 'error'

export interface FinYear {
  period: string
  revenue: number | null
  netProfit: number | null
}

export interface Business {
  durability: 'Strong' | 'Moderate' | 'Weak'
  aiImpact: string
  watch: string
  revenueLabel: string
}

export interface Scores {
  stability: number
  financial: number
  dataQuality: number
  evidence: number
}

export interface Stock {
  symbol: string
  name: string
  industry: string
  status: StockStatus
  lastPrice: number
  /** Empty when the price source did not answer. */
  priceAsOf: string
  priceSource?: string
  referenceHigh: number
  belowHighPct: number
  zone: number
  lotSize: number | null
  isLender: boolean
  falls10: number
  recovered12mPct: number
  longestRecoveryDays: number
  maxDrawdownPct: number
  historyYears: number
  financials: FinYear[]
  debtToEquity: number | null
  promoterPledgePct: number | null
  business: Business
  scores: Scores
  needs: string[]
  history: number[]
}

export interface PlanStep {
  step: number
  levelPct: number
  levelPrice: number
  amount: number
  instrument: Instrument
  quantity: number
  reached: boolean
  filled: boolean
}

export interface Recommendation {
  id: string
  symbol: string
  name: string
  zone: number
  instrumentType: InstrumentType
  steps: PlanStep[]
  targetPrice: number
  hardExitPrice: number
  evidenceScore: number
  reasons: string[]
  risks: string[]
  futuresNote: string
  status: RecStatus
  createdAt: string
}

export interface Position {
  id: string
  symbol: string
  name: string
  mode: Mode
  instrument: Instrument
  quantity: number
  avgPrice: number
  lastPrice: number
  charges: number
  unrealised: number
  openedAt: string
}

export interface TradeLogEntry {
  id: string
  at: string
  symbol: string
  mode: Mode
  side: 'buy' | 'sell'
  instrument: Instrument
  quantity: number
  price: number
  charges: number
  source: string
}

export interface Pnl {
  invested: number
  unrealised: number
  realised: number
  charges: number
}

export interface RunStep {
  seq: number
  at: string
  subject: string
  level: StepLevel
  message: string
}

export interface Run {
  id: string
  kind: RunKind
  /** Set by the server; the sample data has finished runs only. */
  status?: RunStatus
  startedAt: string
  summary: string
  steps: RunStep[]
}

export interface Settings {
  paperCapital: number
  perStockCapPct: number
  levels: number[]
  parts: number[]
  hardExitPct: number
  pauseDrawdownPct: number
  killSwitch: boolean
  alwaysOn: boolean
  realLocked: boolean
  broker: string | null
}

export interface Session {
  email: string
}

export interface RecFilter {
  instrumentType?: InstrumentType | 'any'
  minZone?: number
  minScore?: number
  status?: RecStatus | 'any'
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
  ) {
    super(message)
  }
}

export interface Api {
  signIn(email: string, password: string): Promise<Session>
  listStocks(): Promise<Stock[]>
  getStock(symbol: string): Promise<Stock>
  setStockStatus(symbol: string, status: StockStatus): Promise<Stock>
  listRecommendations(filter?: RecFilter): Promise<Recommendation[]>
  approve(id: string, mode: Mode): Promise<Recommendation>
  skip(id: string, note: string): Promise<Recommendation>
  openTrades(mode: ModeFilter): Promise<Position[]>
  tradeLog(mode: ModeFilter): Promise<TradeLogEntry[]>
  pnl(mode: ModeFilter): Promise<Pnl>
  listRuns(): Promise<Run[]>
  startRun(kind: RunKind): Promise<Run>
  getSettings(): Promise<Settings>
  updateSettings(patch: Partial<Settings>): Promise<Settings>
}
