// Seed data for the mock. Prices and recovery figures are a real snapshot (daily closes to
// 17 Nov 2026 from a public source). Business figures are from the research notes in
// research/2026-11-market-moves/company_research.md; null means "not confirmed".
import type { Business, FinYear, Settings, StockStatus } from '../types'
import snapshot from './prices.snapshot.json'

export interface SeedStock {
  symbol: string
  name: string
  industry: string
  status: StockStatus
  lotSize: number | null
  isLender: boolean
  financials: FinYear[]
  debtToEquity: number | null
  promoterPledgePct: number | null
  business: Business
}

const fy = (values: Array<[number | null, number | null]>): FinYear[] =>
  ['FY2022', 'FY2023', 'FY2024', 'FY2025', 'FY2026'].map((period, i) => ({
    period,
    revenue: values[i]?.[0] ?? null,
    netProfit: values[i]?.[1] ?? null,
  }))

export const SEED_STOCKS: SeedStock[] = [
  {
    symbol: 'ICICIBANK', name: 'ICICI Bank', industry: 'Financial services', status: 'approved', lotSize: 700, isLender: true,
    financials: fy([[47467, 23339], [62128, 31896], [74306, 40888], [81165, 47227], [88075, 50147]]),
    debtToEquity: null, promoterPledgePct: 0,
    business: { durability: 'Strong', aiImpact: 'Helps: lowers the cost of lending checks and service', watch: 'Chief executive succession; lending margin slipped to 4.18%', revenueLabel: 'Net interest income' },
  },
  {
    symbol: 'NESTLEIND', name: 'Nestle India', industry: 'Consumer goods', status: 'approved', lotSize: null, isLender: false,
    financials: fy([[16897, 2391], [null, null], [19563, 3196], [20202, 3208], [23155, 3499]]),
    debtToEquity: null, promoterPledgePct: null,
    business: { durability: 'Strong', aiImpact: 'Little change', watch: 'Food regulator cases on infant formula (Sep-Oct 2026)', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'PIDILITIND', name: 'Pidilite', industry: 'Chemicals', status: 'approved', lotSize: null, isLender: false,
    financials: fy([[9921, 1207], [11799, 1289], [12337, 1747], [13140, 2096], [14601, 2471]]),
    debtToEquity: null, promoterPledgePct: 0,
    business: { durability: 'Strong', aiImpact: 'Little change', watch: 'New competitors in waterproofing', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'TITAN', name: 'Titan', industry: 'Jewellery and watches', status: 'approved', lotSize: null, isLender: false,
    financials: fy([[28799, 2198], [40575, 3274], [51084, 3496], [60456, 3337], [87584, 5073]]),
    debtToEquity: 1.5, promoterPledgePct: 0,
    business: { durability: 'Strong', aiImpact: 'Helps a little', watch: 'Gold-on-lease and borrowings rising; lab-grown diamonds', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'MARICO', name: 'Marico', industry: 'Consumer goods', status: 'approved', lotSize: null, isLender: false,
    financials: fy([[9512, 1255], [9764, 1322], [9653, 1502], [10831, 1658], [13611, 1813]]),
    debtToEquity: 0.09, promoterPledgePct: 0,
    business: { durability: 'Strong', aiImpact: 'Little change', watch: 'Depends on two brands; Bangladesh exposure', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'TORNTPHARM', name: 'Torrent Pharma', industry: 'Healthcare', status: 'watching', lotSize: null, isLender: false,
    financials: fy([[8508, 777], [9620, 1245], [10728, 1656], [11516, 1911], [13980, 2138]]),
    debtToEquity: null, promoterPledgePct: null,
    business: { durability: 'Strong', aiImpact: 'Little change', watch: 'Borrowings rose from 3,202 to 15,026 crore for an acquisition', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'PHOENIXLTD', name: 'Phoenix Mills', industry: 'Realty', status: 'watching', lotSize: null, isLender: false,
    financials: fy([[1460, 268], [2616, 1478], [3972, 1333], [3807, 1307], [4418, 1557]]),
    debtToEquity: 0.47, promoterPledgePct: 0,
    business: { durability: 'Strong', aiImpact: 'Little change', watch: 'Debt rising to buy out a partner', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'INDHOTEL', name: 'Indian Hotels', industry: 'Hotels', status: 'watching', lotSize: null, isLender: false,
    financials: fy([[3056, -265], [5810, 1053], [6769, 1330], [8335, 2038], [9689, 2247]]),
    debtToEquity: null, promoterPledgePct: null,
    business: { durability: 'Strong', aiImpact: 'Little change', watch: 'Earnings swing with the travel cycle', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'KEI', name: 'KEI Industries', industry: 'Cables and wires', status: 'watching', lotSize: null, isLender: false,
    financials: fy([[5727, 376], [6912, 477], [8104, 581], [9736, 696], [11748, 918]]),
    debtToEquity: 0.05, promoterPledgePct: 0,
    business: { durability: 'Moderate', aiImpact: 'Helps indirectly: data centres need cables', watch: 'Large new entrants adding capacity', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'COFORGE', name: 'Coforge', industry: 'IT services', status: 'rejected', lotSize: null, isLender: false,
    financials: fy([[6432, 715], [8015, 745], [9009, 836], [12073, 936], [16403, 1745]]),
    debtToEquity: 0.27, promoterPledgePct: 0,
    business: { durability: 'Moderate', aiImpact: 'Hurts: AI is cutting prices for its core work', watch: 'Growth by acquisition; chairman resigned in Sep 2026', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'SOLARINDS', name: 'Solar Industries', industry: 'Explosives and defence', status: 'rejected', lotSize: null, isLender: false,
    financials: fy([[3948, 455], [6923, 811], [6070, 875], [7540, 1288], [9838, 1737]]),
    debtToEquity: null, promoterPledgePct: 1.5,
    business: { durability: 'Moderate', aiImpact: 'Helps a little', watch: 'Large debt-funded acquisition; ratings on watch', revenueLabel: 'Revenue' },
  },
  {
    symbol: 'NAVINFLUOR', name: 'Navin Fluorine', industry: 'Chemicals', status: 'rejected', lotSize: null, isLender: false,
    financials: fy([[1453, 263], [2077, 375], [2065, 270], [2349, 289], [3314, 664]]),
    debtToEquity: 0.28, promoterPledgePct: 0,
    business: { durability: 'Moderate', aiImpact: 'Helps a little', watch: 'Lumpy profits; low promoter stake; management churn', revenueLabel: 'Revenue' },
  },
]

export interface Snapshot {
  symbol: string
  last: number
  asof: string
  ref: number
  below: number
  falls10: number
  rec12: number
  longest: number
  maxdd: number
  ruledrop: number | null
  years: number
  hist: number[]
}

export const SNAPSHOT = snapshot as Snapshot[]

export const DEFAULT_SETTINGS: Settings = {
  paperCapital: 2000000,
  perStockCapPct: 20,
  levels: [10, 20, 30],
  parts: [1, 2, 3],
  hardExitPct: 40,
  pauseDrawdownPct: 25,
  killSwitch: false,
  alwaysOn: true,
  realLocked: true,
  broker: null,
}

export const DEMO_EMAIL = 'demo@steady.app'
export const DEMO_PASSWORD = 'paper-trading'
export const MOCK_NOW = '2026-11-17T15:25:00+05:30'
