// Every fixed name, label and message the interface uses, in one place.
import type { Instrument, InstrumentType, Mode, RecStatus, RunKind, StockStatus } from './api/types'

export const SESSION_KEY = 'steady.session'
export const HEALTH_URL = '/api/health'
export const STOCKS_URL = '/api/stocks'
export const LIVE_MODE = 'live'
export const BANNER_MOCK = 'Sample data: prices are a snapshot from 17 Nov 2026 and trades are paper only. Nothing here is sent to a broker.'
export const BANNER_LIVE = 'Stock prices and scores are live from the server (daily closes from a public source). Ideas, trades and runs still use sample data. Nothing is sent to a broker.'
export const NEEDS_DATA = 'Needs data'
export const SNAPSHOT_SOURCE = 'sample snapshot'
export const MOCK_DELAY_MS = 150
export const HARD_EXIT_PCT = 40
export const DEFAULT_ERROR = 'Something went wrong.'
export const SIGN_IN_ERROR = 'Could not sign in.'

export const ROUTES = {
  signIn: '/sign-in',
  stocks: '/stocks',
  ideas: '/ideas',
  trades: '/trades',
  runs: '/runs',
  settings: '/settings',
} as const

export const NAV_LINKS = [
  { to: ROUTES.stocks, label: 'Stocks' },
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
