import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { api, resetMockApi } from './api'
import { DEMO_EMAIL, DEMO_PASSWORD, MOCK_SCREEN } from './api/mock/data'
import { ApiError } from './api/types'

function open(route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  )
}
async function signIn(user = userEvent.setup()) {
  await user.type(screen.getByLabelText('Email'), DEMO_EMAIL)
  await user.type(screen.getByLabelText('Password'), DEMO_PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  return user
}
async function openSignedIn(route: string) {
  sessionStorage.setItem('steady.session', JSON.stringify({ email: DEMO_EMAIL }))
  open(route)
  return userEvent.setup()
}

beforeEach(() => resetMockApi())
afterEach(() => vi.unstubAllGlobals())

describe('sign in', () => {
  it('sends you to sign in when there is no session', () => {
    open('/trades')
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })
  it('shows field messages for empty fields and sends nothing (U01)', async () => {
    open('/sign-in')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByText('Enter your email.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')
  })
  it('rejects something that is not an email', async () => {
    open('/sign-in')
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('Password'), 'x')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByText('That does not look like an email address.')).toBeInTheDocument()
  })
  it('shows one generic error and clears the password when it is wrong (U02)', async () => {
    open('/sign-in')
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Email'), DEMO_EMAIL)
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is not right.')
    expect(screen.getByLabelText('Password')).toHaveValue('')
  })
  it('signs in, lands on the page first asked for, keeps the session, and signs out (U03)', async () => {
    const view = open('/trades')
    const user = await signIn()
    expect(await screen.findByRole('heading', { name: 'Trades' })).toBeInTheDocument()
    view.unmount()
    open('/stocks')
    expect(await screen.findByRole('heading', { name: 'Stocks' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })
  it('skips the sign-in page when already signed in, and sends unknown addresses to Stocks', async () => {
    await openSignedIn('/sign-in')
    expect(await screen.findByRole('heading', { name: 'Stocks' })).toBeInTheDocument()
  })
})

describe('stocks', () => {
  it('lists the stocks, filters by status and zone, and sorts (U04)', async () => {
    const user = await openSignedIn('/nowhere')
    expect(await screen.findByRole('link', { name: 'Nestle India' })).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(13)
    await user.selectOptions(screen.getByLabelText('Status'), 'approved')
    expect(screen.getAllByRole('row')).toHaveLength(6)
    await user.click(screen.getByLabelText('Only stocks in a buy zone'))
    expect(screen.getAllByRole('row')).toHaveLength(2)
    expect(screen.getByText('Buy zone 1')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Status'), 'rejected')
    await user.click(screen.getByLabelText('Only stocks in a buy zone'))
    await user.click(screen.getByRole('button', { name: /^Stock/ }))
    expect(within(screen.getAllByRole('row')[1]!).getByRole('link')).toHaveTextContent('Coforge')
    await user.click(screen.getByRole('button', { name: /Below 6-month high/ }))
    expect(within(screen.getAllByRole('row')[1]!).getByRole('link')).toHaveTextContent('Solar Industries')
    await user.click(screen.getByRole('button', { name: /Below 6-month high/ }))
    expect(within(screen.getAllByRole('row')[1]!).getByRole('link')).not.toHaveTextContent('Solar Industries')
    for (const name of [/Status/, /Price/, /Zone/, /Evidence score/, /Needs data/]) await user.click(screen.getByRole('button', { name }))
    expect(screen.getAllByRole('row')).toHaveLength(4)
    expect(screen.getByRole('list', { name: 'About this page' })).toHaveTextContent('Latest price: 17 Nov 2026')
  })
  it('says when no stock matches', async () => {
    await api.setStockStatus('KEI', 'approved')
    const user = await openSignedIn('/stocks')
    await screen.findByRole('link', { name: 'Titan' })
    await user.selectOptions(screen.getByLabelText('Status'), 'watching')
    await user.click(screen.getByLabelText('Only stocks in a buy zone'))
    expect(screen.getByText('No stocks match these filters.')).toBeInTheDocument()
  })
  it('shows levels, score parts and exactly what data is missing (U05)', async () => {
    await openSignedIn('/stocks/NESTLEIND')
    expect(await screen.findByRole('heading', { name: 'Nestle India' })).toBeInTheDocument()
    expect(screen.getByText('₹1,386.00')).toBeInTheDocument()
    expect(screen.getByText('Net profit for FY2023')).toBeInTheDocument()
    expect(screen.getByText('Futures lot size')).toBeInTheDocument()
    expect(screen.getAllByText('Needs data').length).toBeGreaterThan(1)
    expect(screen.getByRole('img', { name: /Recovery from falls/ })).toBeInTheDocument()
  })
  it('shows a stock that is not in a buy zone', async () => {
    await openSignedIn('/stocks/TITAN')
    expect(await screen.findByRole('heading', { name: 'Titan' })).toBeInTheDocument()
    expect(screen.getByText(/Not in a buy zone/)).toBeInTheDocument()
  })
  it('lets you approve, watch or reject a stock', async () => {
    const user = await openSignedIn('/stocks/KEI')
    await user.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled())
    await user.click(screen.getByRole('button', { name: 'Reject' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Reject' })).toBeDisabled())
    await user.click(screen.getByRole('button', { name: 'Keep watching' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Keep watching' })).toBeDisabled())
  })
  it('shows an error for an unknown stock', async () => {
    await openSignedIn('/stocks/NOPE')
    expect(await screen.findByRole('alert')).toHaveTextContent('Unknown stock NOPE')
  })
})

describe('ideas', () => {
  it('shows the idea with its type, plan and evidence (U06)', async () => {
    await openSignedIn('/ideas')
    const card = await screen.findByRole('article', { name: 'Idea for Nestle India' })
    expect(within(card).getByText('Buy: Shares')).toBeInTheDocument()
    expect(within(card).getByText('₹66,666')).toBeInTheDocument()
    expect(within(card).getAllByRole('row')).toHaveLength(4)
    expect(within(card).getByText(/lot size needs data/)).toBeInTheDocument()
  })
  it('defaults to paper, and locks approve with a reason when real is chosen (U07)', async () => {
    const user = await openSignedIn('/ideas')
    const card = await screen.findByRole('article', { name: 'Idea for Nestle India' })
    expect(within(card).getByLabelText('Paper trade')).toBeChecked()
    await user.click(within(card).getByLabelText('Real trade'))
    expect(within(card).getByRole('status')).toHaveTextContent('Real trading is locked')
    expect(within(card).getByRole('button', { name: 'Approve step 1' })).toBeDisabled()
    await user.click(within(card).getByLabelText('Paper trade'))
    expect(within(card).getByRole('button', { name: 'Approve step 1' })).toBeEnabled()
  })
  it('approves a paper trade, which then appears in Trades with profit or loss (U08, E02)', async () => {
    const user = await openSignedIn('/ideas')
    const card = await screen.findByRole('article', { name: 'Idea for Nestle India' })
    await user.click(within(card).getByRole('button', { name: 'Approve step 1' }))
    await waitFor(() => expect(within(screen.getByRole('article', { name: 'Idea for Nestle India' })).getByText('Approved')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Approve step 1' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Trades' }))
    expect(await screen.findByRole('link', { name: 'Nestle India' })).toBeInTheDocument()
    expect(screen.getByText('₹66,221')).toBeInTheDocument()
    expect(screen.getAllByText('▼ −₹33')).toHaveLength(2)
  })
  it('shows the reason when an approval fails', async () => {
    const user = await openSignedIn('/ideas')
    const card = await screen.findByRole('article', { name: 'Idea for Nestle India' })
    await api.updateSettings({ killSwitch: true })
    await user.click(within(card).getByRole('button', { name: 'Approve step 1' }))
    expect(await within(card).findByRole('alert')).toHaveTextContent('New orders are stopped')
  })
  it('skips an idea and filters the list', async () => {
    const user = await openSignedIn('/ideas')
    const card = await screen.findByRole('article', { name: 'Idea for Nestle India' })
    await user.click(within(card).getByRole('button', { name: 'Skip' }))
    await waitFor(() => expect(within(screen.getByRole('article', { name: 'Idea for Nestle India' })).getByText('Skipped')).toBeInTheDocument())
    await user.selectOptions(screen.getByLabelText('State'), 'new')
    expect(await screen.findByText(/No ideas match/)).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('State'), 'any')
    await user.selectOptions(screen.getByLabelText('Buy with'), 'future')
    expect(await screen.findByText(/No ideas match/)).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Buy with'), 'any')
    await user.selectOptions(screen.getByLabelText('Deepest zone at least'), '2')
    expect(await screen.findByText(/No ideas match/)).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Deepest zone at least'), '0')
    await user.selectOptions(screen.getByLabelText('Evidence score at least'), '80')
    expect(await screen.findByText(/No ideas match/)).toBeInTheDocument()
  })
})

describe('trades', () => {
  it('starts empty, and switches between paper, real and all (U09)', async () => {
    const user = await openSignedIn('/trades')
    expect(await screen.findByText('No open trades yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See ideas waiting for you' })).toBeInTheDocument()
    const [rec] = await api.listRecommendations()
    await api.approve(rec!.id, 'paper')
    await user.click(screen.getByRole('button', { name: 'Real' }))
    expect(await screen.findByText('No real trades. Real trading is locked.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Real' })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getByRole('button', { name: 'All' }))
    expect(await screen.findByRole('link', { name: 'Nestle India' })).toBeInTheDocument()
    expect(screen.getByText('Bought shares')).toBeInTheDocument()
    expect(screen.getAllByText('Paper').length).toBeGreaterThan(1)
    for (const name of [/^Stock/, /Quantity/, /Average price/, /Last price/, /Profit or loss/]) await user.click(screen.getByRole('button', { name }))
    expect(screen.getByRole('columnheader', { name: /Profit or loss/ })).toHaveAttribute('aria-sort', 'descending')
    expect(screen.getByRole('list', { name: 'About this page' })).toHaveTextContent('sample data')
  })
})

describe('screener', () => {
  const deep = (): typeof MOCK_SCREEN => ({
    ...MOCK_SCREEN, market: 'deep', marketBelowPct: 17.3,
    rows: MOCK_SCREEN.rows.map((r, i) => ({ ...r, confidence: i === 1 ? 'high' : i === 4 ? 'medium' : 'low', evidence: r.evidence.map((e) => ({ ...e, met: i === 1 })) })),
  })
  it('says there is no high-confidence buy today, and why', async () => {
    await openSignedIn('/screener')
    expect(await screen.findByText('Market not in a fall')).toBeInTheDocument()
    expect(screen.getByText(/Nifty is 2.1% below its 1-year high\. The market is not/)).toHaveTextContent('coin toss')
    expect(screen.getByRole('heading', { name: 'High-confidence buys today (0)' })).toBeInTheDocument()
    expect(screen.getByText('None today. Nifty is 2.1% below its 1-year high.')).toBeInTheDocument()
    expect(screen.getByText(/0 stocks at medium confidence and 5 at low/)).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'About this page' })).toHaveTextContent('not real time. Latest price: 17 Nov 2026.')
    expect(screen.getByText(/prices for 499 of 501 stocks/)).toBeInTheDocument()
  })
  it('lists the fallen stocks with confidence, odds and the evidence behind them', async () => {
    const user = await openSignedIn('/screener')
    const fallen = await screen.findByRole('table', { name: 'Stocks in a deep fall' })
    expect(within(fallen).getAllByRole('row')).toHaveLength(6)
    const kpit = within(fallen).getByText('KPIT Technologies').closest('tr')!
    expect(kpit).toHaveTextContent('Low')
    expect(kpit).toHaveTextContent('59.0%')
    expect(kpit).toHaveTextContent('51%')
    expect(kpit).toHaveTextContent('5 of 7 higher after a year')
    await user.click(within(kpit).getByText('Evidence'))
    expect(within(kpit).getByText(/a market-wide fall starts at 10%/)).toBeInTheDocument()
    expect(within(kpit).getAllByLabelText('No')).toHaveLength(3)
    expect(within(kpit).getAllByLabelText('Yes')).toHaveLength(2)
    expect(within(fallen).getByText(/Fell 62% in one day/)).toBeInTheDocument()
    const odds = screen.getByRole('table', { name: 'What happened after past falls' })
    expect(within(odds).getAllByRole('row')).toHaveLength(13)
    expect(within(odds).getAllByText('Deep fall (15% or more)')).toHaveLength(4)
  })
  it('filters by fall size and search, and sorts by column', async () => {
    const user = await openSignedIn('/screener')
    await user.selectOptions(await screen.findByLabelText('Fell at least'), '40')
    expect(screen.getByRole('heading', { name: 'Stocks in a deep fall today (4)' })).toBeInTheDocument()
    const fallen = screen.getByRole('table', { name: 'Stocks in a deep fall' })
    expect(within(fallen).getAllByRole('row')[1]).toHaveTextContent('Vedanta')
    await user.click(within(fallen).getByRole('button', { name: /^Stock/ }))
    expect(within(fallen).getAllByRole('row')[1]).toHaveTextContent('KPIT Technologies')
    await user.click(within(fallen).getByRole('button', { name: /Price/ }))
    expect(within(fallen).getAllByRole('row')[1]).toHaveTextContent('PI Industries')
    await user.type(screen.getByLabelText('Find'), 'zzz')
    expect(screen.getByText('No stock matches.')).toBeInTheDocument()
  })
  it('shows high-confidence buys with their evidence in a deep market fall', async () => {
    vi.spyOn(api, 'getScreen').mockResolvedValue({ running: false, error: null, screen: deep() })
    await openSignedIn('/screener')
    expect(await screen.findByText('Deep market fall')).toBeInTheDocument()
    expect(screen.getByText(/Nifty is 17.3% below/)).toHaveTextContent('worked best')
    expect(screen.getByRole('heading', { name: 'High-confidence buys today (1)' })).toBeInTheDocument()
    const pick = screen.getByRole('group', { name: 'Pick KPIT Technologies' })
    expect(pick).toHaveTextContent('After similar falls: 88% higher after 6 months, 92% after a year; 33% fell another 20% first.')
    expect(within(pick).getAllByLabelText('Yes')).toHaveLength(5)
    const fallen = screen.getByRole('table', { name: 'Stocks in a deep fall' })
    expect(within(fallen).getAllByRole('row')[1]).toHaveTextContent('KPIT Technologies')
    expect(within(fallen).getByText('Medium')).toBeInTheDocument()
  })
  it('names a plain market fall, and shows dashes when there are no odds or rows', async () => {
    vi.spyOn(api, 'getScreen').mockResolvedValue({ running: false, error: null, screen: { ...deep(), market: 'down', odds: [] } })
    await openSignedIn('/screener')
    expect(await screen.findByText('Market in a fall')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Pick KPIT Technologies' })).toHaveTextContent('After similar falls: – higher')
    cleanup()
    vi.spyOn(api, 'getScreen').mockResolvedValue({ running: false, error: null, screen: { ...MOCK_SCREEN, rows: [] } })
    await openSignedIn('/screener')
    expect(await screen.findByText('No stock matches.')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'About this page' })).not.toHaveTextContent('Latest price')
  })
  it('screens again on demand', async () => {
    const user = await openSignedIn('/screener')
    const start = vi.spyOn(api, 'startScreen')
    await user.click(await screen.findByRole('button', { name: 'Screen now' }))
    await waitFor(() => expect(start).toHaveBeenCalledOnce())
    expect(await screen.findByRole('button', { name: 'Screen now' })).toBeEnabled()
  })
  it('explains when there is no screen yet, and when one is running', async () => {
    vi.spyOn(api, 'getScreen').mockResolvedValue({ running: true, error: null, screen: null })
    await openSignedIn('/screener')
    expect(await screen.findByText(/No screen yet/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Screening…' })).toBeDisabled()
  })
  it('shows why a screen failed', async () => {
    vi.spyOn(api, 'getScreen').mockResolvedValue({ running: false, error: 'The screen failed.', screen: null })
    const user = await openSignedIn('/screener')
    expect(await screen.findByRole('alert')).toHaveTextContent('The screen failed.')
    vi.spyOn(api, 'startScreen').mockRejectedValue(new ApiError('The server did not answer.', 'network'))
    await user.click(screen.getByRole('button', { name: 'Screen now' }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('The server did not answer.'))
  })
})

describe('algo runs', () => {
  it('shows the reasoning in order and adds a new run on demand (U11)', async () => {
    const user = await openSignedIn('/runs')
    const steps = await screen.findByRole('list', { name: 'Run steps' })
    const items = within(steps).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Prices')
    expect(items[items.length - 1]).toHaveTextContent('1 idea proposed')
    await user.click(screen.getByRole('button', { name: 'Dry run' }))
    expect(await screen.findByText(/Dry run run/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Run now' }))
    expect(await screen.findByText(/On demand run/)).toBeInTheDocument()
    const earlier = screen.getAllByRole('button', { name: /Scheduled/ })
    await user.click(earlier[earlier.length - 1]!)
    expect(await screen.findByText(/Scheduled run/)).toBeInTheDocument()
  })
  it('turns Always on off and on', async () => {
    const user = await openSignedIn('/runs')
    const toggle = await screen.findByRole('switch', { name: 'Always on' })
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'))
    await user.click(toggle)
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'))
    expect(screen.getByText(/Paused/)).toBeInTheDocument()
  })
})

describe('settings', () => {
  it('shows paper in use and real locked, and stops and allows new orders', async () => {
    const user = await openSignedIn('/settings')
    expect(await screen.findByText('In use')).toBeInTheDocument()
    expect(screen.getByText('Locked')).toBeInTheDocument()
    expect(screen.getByText('₹20,00,000')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Stop all new orders' }))
    expect(await screen.findByText('Stopped')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Allow new orders' }))
    expect(await screen.findByText('Allowed')).toBeInTheDocument()
  })
})

describe('backend status', () => {
  const answer = (ok: boolean, body: unknown) => vi.fn().mockResolvedValue({ ok, json: () => Promise.resolve(body) })
  it('says connected, with the version, when the server answers', async () => {
    vi.stubGlobal('fetch', answer(true, { status: 'ok', service: 'steady', version: 'abcdef1234', time: 'now' }))
    await openSignedIn('/settings')
    expect(await screen.findByText('Connected')).toBeInTheDocument()
    expect(screen.getByText(/version abcdef1\)/)).toBeInTheDocument()
  })
  it('says not connected when the server is missing, failing or unhealthy', async () => {
    for (const fetchMock of [vi.fn().mockRejectedValue(new Error('offline')), answer(false, {}), answer(true, { status: 'down' })]) {
      vi.stubGlobal('fetch', fetchMock)
      await openSignedIn('/settings')
      expect(await screen.findByText(/No server is answering/)).toBeInTheDocument()
      cleanup()
    }
  })
})
