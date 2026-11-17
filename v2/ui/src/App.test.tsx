import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { api, resetMockApi } from './api'
import { DEMO_EMAIL, DEMO_PASSWORD } from './api/mock/data'

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
    await user.selectOptions(screen.getByLabelText('Sort by'), 'name')
    expect(within(screen.getAllByRole('row')[1]!).getByRole('link')).toHaveTextContent('Coforge')
    await user.selectOptions(screen.getByLabelText('Sort by'), 'below')
    expect(within(screen.getAllByRole('row')[1]!).getByRole('link')).toHaveTextContent('Solar Industries')
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
