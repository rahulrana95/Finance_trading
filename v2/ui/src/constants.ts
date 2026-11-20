// Every fixed name, label and message the interface uses, in one place.
import type { Confidence, Instrument, InstrumentType, MarketState, Mode, RecStatus, RunKind, StockStatus } from './api/types'

export const SESSION_KEY = 'steady.session'
export const HEALTH_URL = '/api/health'
export const STOCKS_URL = '/api/stocks'
export const RUNS_URL = '/api/runs'
export const IDEAS_URL = '/api/recommendations'
export const SCREENS_URL = '/api/screens'
export const SCREEN_POLL_TRIES = 180
export const DEMERGER_DROP_PCT = 35
export const RUN_POLL_MS = 1000
export const RUN_POLL_TRIES = 60
export const LIVE_MODE = 'live'
export const BANNER_MOCK = 'Sample data: prices are a snapshot from 17 Nov 2026 and trades are paper only. Nothing here is sent to a broker.'
export const BANNER_LIVE = 'Stocks, the screener, ideas and algo runs are live from the server (daily closes from a public source). Trades and settings still use sample data. Nothing is sent to a broker.'
export const NEEDS_DATA = 'Needs data'
export const SNAPSHOT_SOURCE = 'sample snapshot'
export const MOCK_DELAY_MS = 150
export const HARD_EXIT_PCT = 40
export const DEFAULT_ERROR = 'Something went wrong.'
export const SIGN_IN_ERROR = 'Could not sign in.'

export const ROUTES = {
  signIn: '/sign-in',
  stocks: '/stocks',
  screener: '/screener',
  ideas: '/ideas',
  trades: '/trades',
  runs: '/runs',
  settings: '/settings',
} as const

export const NAV_LINKS = [
  { to: ROUTES.stocks, label: 'Stocks' },
  { to: ROUTES.screener, label: 'Screener' },
  { to: ROUTES.ideas, label: 'Ideas' },
  { to: ROUTES.trades, label: 'Trades' },
  { to: ROUTES.runs, label: 'Algo runs' },
  { to: ROUTES.settings, label: 'Settings' },
] as const

export const MODE_LABEL: Record<Mode, string> = { paper: 'Paper', real: 'Real' }
export const INSTRUMENT_LABEL: Record<Instrument, string> = { cash: 'Shares', future: 'Futures' }
export const INSTRUMENT_TYPE_LABEL: Record<InstrumentType, string> = { cash: 'Shares', future: 'Futures', combo: 'Shares and futures' }
export const SIDE_LABEL = { buy: 'Bought', sell: 'Sold' } as const
export const STOCK_STATUS_LABEL: Record<StockStatus, string> = { approved: 'Approved', watching: 'Watching', rejected: 'Rejected' }
export const STOCK_STATUS_KIND = { approved: 'good', watching: 'neutral', rejected: 'bad' } as const
export const REC_STATUS_LABEL: Record<RecStatus, string> = { new: 'Waiting for you', approved: 'Approved', skipped: 'Skipped', expired: 'Expired' }
export const RUN_KIND_LABEL: Record<RunKind, string> = { scheduled: 'Scheduled', on_demand: 'On demand', dry_run: 'Dry run', screener: 'Screener' }
export const BROKERS = ['Zerodha', 'Dhan', 'Groww'] as const
export const IDEA_READ_ONLY = 'Ideas are shown only for now. Approving one from here arrives with sign-in on the server.'
export const ALWAYS_ON_TEXT = 'Checks every 5 minutes while the market is open.'
export const ALWAYS_ON_SERVER = 'Running on the server, Monday to Friday, 09:15 to 15:30 India time.'
export const SCREEN_CAVEAT = 'Chances are how often it happened after similar falls since 2016, across these stocks. They describe the past and are not a promise. The list holds today\u2019s index members only, so companies that failed and left the index are missing and the real figures are somewhat worse.'
export const MARKET_LABEL: Record<MarketState, string> = { deep: 'Deep market fall', down: 'Market in a fall', fine: 'Market not in a fall' }
export const MARKET_ROW_LABEL: Record<MarketState, string> = { deep: 'Deep fall (15% or more)', down: 'In a fall (10 to 15%)', fine: 'Not in a fall' }
export const MARKET_TEXT: Record<MarketState, string> = {
  deep: 'This is a deep market-wide fall, the case where buying fallen stocks has worked best in every period tested.',
  down: 'The whole market is in a fall. Fallen stocks have done better than usual in this case, but less reliably than in a deep fall.',
  fine: 'The market is not in a fall. Stocks that fall on their own have been close to a coin toss, so treat the list below as a watch list.',
}
export const MARKET_KIND = { deep: 'good', down: 'accent', fine: 'neutral' } as const
export const CONFIDENCE_LABEL: Record<Confidence, string> = { high: 'High', medium: 'Medium', low: 'Low' }
export const CONFIDENCE_KIND = { high: 'good', medium: 'accent', low: 'neutral' } as const
export const CONFIDENCE_RANK: Record<Confidence, number> = { high: 3, medium: 2, low: 1 }
export const NO_HIGH_TEXT = 'High confidence needs a deep market-wide fall (Nifty 15% or more below its 1-year high) and a stock that has fallen 25% or more. That is the only case that held up in both test periods: about 85% of such stocks were higher six months later.'
export const NOT_EVIDENCE_TEXT = 'A stock\u2019s own past recoveries, its size and its long-term trend are not part of the confidence: in the tests they did not change the odds.'
export const PRICES_NOT_LIVE = 'Prices are daily closing prices from a public source, not real time.'
export const PAGE_NOTES = {
  stocks: ['The 12 stocks we researched one by one: business, sales, profit, debt and how they recovered from past falls.', 'Approved stocks that fall 10% or more below their 6-month high get a buy idea on the Ideas page.'],
  screener: ['Checks about 500 stocks for falls of 20% or more from their 1-year high, and shows how similar falls turned out since 2016.', 'Confidence is High only when the whole market is in a deep fall; press Evidence on any row to see why.'],
  ideas: ['Buy ideas from the algo for approved stocks in a buy zone, each with a step-by-step plan, a target and an exit.', 'Ideas refresh every 5 minutes in market hours. They are view only until sign-in is built.'],
  trades: ['Paper trades you approved, with profit or loss.', 'This page still uses sample data in your browser; nothing here is a real trade and nothing is sent to a broker.'],
  runs: ['A plain-word log of every check the algo made and what it decided.', 'It runs by itself every 5 minutes on weekdays from 09:15 to 15:30 India time, and when you press Run now.'],
  settings: ['Paper money, step sizes, exits and the stop switch.', 'These settings are sample values in your browser for now; the server uses the fixed rules in the design document.'],
} as const
