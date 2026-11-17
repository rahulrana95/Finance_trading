import { beforeEach, describe, expect, it } from 'vitest'
import type { Api } from '../types'
import { DEMO_EMAIL, DEMO_PASSWORD } from './data'
import { createMockApi, latestProfit, snapshotFor } from './mockApi'

let api: Api
beforeEach(() => {
  api = createMockApi({ delayMs: 0 })
})

describe('sign in', () => {
  it('accepts the demo account, ignoring case and spaces in the email', async () =>
    expect(await api.signIn(`  ${DEMO_EMAIL.toUpperCase()} `, DEMO_PASSWORD)).toEqual({ email: DEMO_EMAIL }))
  it('rejects a wrong password with one generic message', async () =>
    await expect(api.signIn(DEMO_EMAIL, 'nope')).rejects.toThrow('Email or password is not right.'))
  it('locks after five failures, even for the right password', async () => {
    for (let i = 0; i < 5; i++) await api.signIn(DEMO_EMAIL, 'x').catch(() => undefined)
    await expect(api.signIn(DEMO_EMAIL, DEMO_PASSWORD)).rejects.toThrow('Too many attempts')
  })
})

describe('stocks', () => {
  it('seeds twelve stocks with scores and needs (D04)', async () => {
    const stocks = await api.listStocks()
    expect(stocks).toHaveLength(12)
    expect(stocks.filter((s) => s.status === 'approved').map((s) => s.symbol)).toEqual(['ICICIBANK', 'NESTLEIND', 'PIDILITIND', 'TITAN', 'MARICO'])
    const nestle = stocks.find((s) => s.symbol === 'NESTLEIND')!
    expect(nestle.zone).toBe(1)
    expect(nestle.needs).toEqual(expect.arrayContaining(['Net profit for FY2023', 'Debt and equity', 'Promoter pledge', 'Futures lot size']))
    expect(nestle.scores.evidence).toBeGreaterThan(0)
  })
  it('returns one stock and rejects an unknown symbol (H06)', async () => {
    expect((await api.getStock('TITAN')).name).toBe('Titan')
    await expect(api.getStock('NOPE')).rejects.toThrow('Unknown stock NOPE')
  })
  it('changes a stock status', async () => expect((await api.setStockStatus('KEI', 'approved')).status).toBe('approved'))
  it('returns copies, so callers cannot change the stored state', async () => {
    const first = await api.listStocks()
    first[0]!.name = 'changed'
    expect((await api.listStocks())[0]!.name).toBe('ICICI Bank')
  })
})

describe('runs and ideas', () => {
  it('starts with one scheduled run that proposed Nestle (G02) and ignored unapproved stocks (G03)', async () => {
    const [run] = await api.listRuns()
    expect(run!.summary).toBe('1 idea proposed')
    expect(run!.steps.map((s) => s.seq)).toEqual(run!.steps.map((_, i) => i + 1))
    expect(run!.steps.find((s) => s.subject === 'Not approved')!.message).toContain('KEI Industries')
    const recs = await api.listRecommendations()
    expect(recs.map((r) => r.symbol)).toEqual(['NESTLEIND'])
    expect(recs[0]!.instrumentType).toBe('cash')
    expect(recs[0]!.steps.map((s) => s.reached)).toEqual([true, false, false])
  })
  it('does not duplicate an idea on a second run (G06)', async () => {
    const run = await api.startRun('on_demand')
    expect(run.summary).toBe('No action')
    expect(await api.listRecommendations()).toHaveLength(1)
  })
  it('creates nothing on a dry run (G07)', async () => {
    const [rec] = await api.listRecommendations()
    await api.skip(rec!.id, '')
    const run = await api.startRun('dry_run')
    expect(run.summary).toBe('Dry run, no orders')
    expect(run.steps.some((s) => s.message.includes('Dry run: no idea created'))).toBe(true)
    expect((await api.listRecommendations()).filter((r) => r.status === 'new')).toHaveLength(0)
  })
  it('proposes nothing new while orders are stopped (G05)', async () => {
    const [rec] = await api.listRecommendations()
    await api.skip(rec!.id, '')
    await api.updateSettings({ killSwitch: true })
    const run = await api.startRun('on_demand')
    expect(run.steps.some((s) => s.message.includes('new orders are stopped'))).toBe(true)
    expect(run.summary).toBe('No action')
  })
  it('says so when every reached step is already bought', async () => {
    const [rec] = await api.listRecommendations()
    await api.approve(rec!.id, 'paper')
    const run = await api.startRun('on_demand')
    expect(run.steps.some((s) => s.message.includes('Every step reached is already bought'))).toBe(true)
  })
  it('filters ideas by type, state, zone and score (H08)', async () => {
    expect(await api.listRecommendations({ instrumentType: 'future' })).toHaveLength(0)
    expect(await api.listRecommendations({ instrumentType: 'cash', status: 'new', minZone: 1, minScore: 10 })).toHaveLength(1)
    expect(await api.listRecommendations({ minZone: 2 })).toHaveLength(0)
    expect(await api.listRecommendations({ minScore: 101 })).toHaveLength(0)
    expect(await api.listRecommendations({ status: 'skipped' })).toHaveLength(0)
  })
})

describe('trading', () => {
  it('fills a paper approval from the market price with slippage and charges, and logs it (T01)', async () => {
    const [rec] = await api.listRecommendations()
    const done = await api.approve(rec!.id, 'paper')
    expect(done.status).toBe('approved')
    const [pos] = await api.openTrades('paper')
    expect(pos).toMatchObject({ symbol: 'NESTLEIND', mode: 'paper', instrument: 'cash', quantity: 51, avgPrice: 1298.45 })
    expect(pos!.unrealised).toBe(-33.15)
    const [fill] = await api.tradeLog('paper')
    expect(fill).toMatchObject({ side: 'buy', quantity: 51, price: 1298.45, charges: 79.47, source: 'Public daily close (snapshot)' })
    expect(await api.pnl('paper')).toEqual({ invested: 66220.95, unrealised: -33.15, realised: 0, charges: 79.47 })
  })
  it('refuses a real trade and creates nothing (T02)', async () => {
    const [rec] = await api.listRecommendations()
    await expect(api.approve(rec!.id, 'real')).rejects.toThrow('Real trading is locked')
    expect(await api.tradeLog('all')).toHaveLength(0)
  })
  it('refuses a second approval (T04) and an unknown idea', async () => {
    const [rec] = await api.listRecommendations()
    await api.approve(rec!.id, 'paper')
    await expect(api.approve(rec!.id, 'paper')).rejects.toThrow('already been handled')
    await expect(api.approve('rec-999', 'paper')).rejects.toThrow('no longer exists')
  })
  it('refuses to buy while orders are stopped', async () => {
    const [rec] = await api.listRecommendations()
    await api.updateSettings({ killSwitch: true })
    await expect(api.approve(rec!.id, 'paper')).rejects.toThrow('New orders are stopped')
  })
  it('skips an idea once (T07)', async () => {
    const [rec] = await api.listRecommendations()
    expect((await api.skip(rec!.id, 'too early')).status).toBe('skipped')
    await expect(api.skip(rec!.id, '')).rejects.toThrow('already been handled')
    await expect(api.skip('rec-999', '')).rejects.toThrow('no longer exists')
  })
  it('keeps paper and real apart in every view (O01, O02)', async () => {
    const [rec] = await api.listRecommendations()
    await api.approve(rec!.id, 'paper')
    expect(await api.openTrades('real')).toHaveLength(0)
    expect(await api.openTrades('all')).toHaveLength(1)
    expect((await api.pnl('real')).invested).toBe(0)
  })
  it('adds to an existing position at the average price when a second step is bought', async () => {
    const api2 = createMockApi({ delayMs: 0 })
    await api2.setStockStatus('KEI', 'approved')
    await api2.startRun('on_demand')
    const rec = (await api2.listRecommendations()).find((r) => r.symbol === 'KEI')!
    expect(rec.steps.filter((s) => s.reached)).toHaveLength(3)
    await api2.approve(rec.id, 'paper')
    const after = await api2.approve(rec.id, 'paper')
    expect(after.status).toBe('new')
    const pos = (await api2.openTrades('paper')).find((p) => p.symbol === 'KEI')!
    expect(pos.quantity).toBe(14 + 28)
    expect(await api2.tradeLog('paper')).toHaveLength(2)
  })
})

describe('settings', () => {
  it('reads and updates settings', async () => {
    expect((await api.getSettings()).paperCapital).toBe(2000000)
    expect((await api.updateSettings({ alwaysOn: false })).alwaysOn).toBe(false)
  })
  it('cannot unlock real trading', async () =>
    await expect(api.updateSettings({ realLocked: false })).rejects.toThrow('cannot be unlocked'))
})

describe('timing', () => {
  it('waits when a delay is set', async () => {
    const slow = createMockApi({ delayMs: 5 })
    const started = Date.now()
    await slow.getSettings()
    expect(Date.now() - started).toBeGreaterThanOrEqual(4)
  })
})

describe('helpers', () => {
  it('finds a price snapshot and fails loudly for a seed without one', () => {
    expect(snapshotFor('TITAN').symbol).toBe('TITAN')
    expect(() => snapshotFor('NOPE')).toThrow('No price snapshot for NOPE')
  })
  it('puts the latest profit in words', () => {
    expect(latestProfit([{ netProfit: 3499 }])).toBe('3,499')
    expect(latestProfit([{ netProfit: null }])).toBe('not known')
    expect(latestProfit([])).toBe('not known')
  })
  it('defaults to a short delay and the fixed clock', async () => {
    const [run] = await createMockApi().listRuns()
    expect(run!.startedAt).toBe('2026-11-17T09:55:00.000Z')
  })
})

describe('edge cases', () => {
  it('proposes two ideas in one run and says so', async () => {
    const [rec] = await api.listRecommendations()
    await api.skip(rec!.id, '')
    await api.setStockStatus('KEI', 'approved')
    expect((await api.startRun('on_demand')).summary).toBe('2 ideas proposed')
  })
  it('refuses a step that is smaller than one share', async () => {
    const [rec] = await api.listRecommendations()
    await api.skip(rec!.id, '')
    await api.updateSettings({ paperCapital: 10000 })
    await api.startRun('on_demand')
    const small = (await api.listRecommendations({ status: 'new' }))[0]!
    expect(small.steps[0]!.quantity).toBe(0)
    await expect(api.approve(small.id, 'paper')).rejects.toThrow('smaller than one share')
  })
})
