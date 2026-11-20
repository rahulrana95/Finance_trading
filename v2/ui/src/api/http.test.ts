import { afterEach, describe, expect, it, vi } from 'vitest'
import { getJson, ideasQuery, liveAlgo, liveScreen, liveStocks, postJson, waitForRun, waitUntil } from './http'
import { sleep } from '../lib/sleep'
import type { Run } from './types'

const reply = (ok: boolean, status: number, body: unknown) =>
  vi.fn().mockResolvedValue({ ok, status, json: () => (body === undefined ? Promise.reject(new Error('no json')) : Promise.resolve(body)) })

afterEach(() => vi.unstubAllGlobals())

describe('getJson', () => {
  it('returns the document', async () => {
    vi.stubGlobal('fetch', reply(true, 200, { a: 1 }))
    expect(await getJson('/x')).toEqual({ a: 1 })
  })
  it("uses the server's reason for a failure", async () => {
    vi.stubGlobal('fetch', reply(false, 404, { detail: 'Unknown stock NOPE' }))
    await expect(getJson('/x')).rejects.toMatchObject({ message: 'Unknown stock NOPE', code: '404' })
  })
  it('falls back to a general message when the failure has no readable reason', async () => {
    for (const body of [{ detail: [{ msg: 'bad' }] }, undefined]) {
      vi.stubGlobal('fetch', reply(false, 500, body))
      await expect(getJson('/x')).rejects.toMatchObject({ message: 'Something went wrong.', code: '500' })
    }
  })
  it('says so when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(getJson('/x')).rejects.toMatchObject({ code: 'network' })
  })
})

describe('live stocks', () => {
  it('reads the list and one stock from the backend', async () => {
    const fetchMock = reply(true, 200, [])
    vi.stubGlobal('fetch', fetchMock)
    await liveStocks.listStocks()
    await liveStocks.getStock('M&M')
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/stocks', '/api/stocks/M%26M'])
  })
})

describe('postJson', () => {
  it('sends the body as JSON', async () => {
    const fetchMock = reply(true, 202, { id: 'r1' })
    vi.stubGlobal('fetch', fetchMock)
    expect(await postJson('/x', { kind: 'dry_run' })).toEqual({ id: 'r1' })
    expect(fetchMock.mock.calls[0]![1]).toMatchObject({ method: 'POST', body: '{"kind":"dry_run"}', headers: { Accept: 'application/json', 'Content-Type': 'application/json' } })
  })
})

describe('ideasQuery', () => {
  it('is empty when nothing narrows the list', () => {
    expect(ideasQuery()).toBe('')
    expect(ideasQuery({ instrumentType: 'any', status: 'any', minZone: 0, minScore: 0 })).toBe('')
  })
  it('sends only the filters that are set', () => {
    expect(ideasQuery({ instrumentType: 'combo', status: 'new', minZone: 2, minScore: 70 })).toBe('?instrumentType=combo&status=new&minZone=2&minScore=70')
    expect(ideasQuery({ minScore: 60 })).toBe('?minScore=60')
  })
})

const run = (status: Run['status']): Run => ({ id: 'r1', kind: 'on_demand', status, startedAt: '', summary: '', steps: [] })

describe('waitForRun', () => {
  it('asks again until the run has finished', async () => {
    const get = vi.fn().mockResolvedValueOnce(run('running')).mockResolvedValueOnce(run('running')).mockResolvedValue(run('done'))
    const wait = vi.fn().mockResolvedValue(undefined)
    expect((await waitForRun('r1', get, wait)).status).toBe('done')
    expect(get).toHaveBeenCalledTimes(3)
    expect(wait.mock.calls).toEqual([[1000], [1000]])
  })
  it('gives up after the allowed number of tries and returns what it has', async () => {
    const get = vi.fn().mockResolvedValue(run('running'))
    expect((await waitForRun('r1', get, () => Promise.resolve(), 3)).status).toBe('running')
    expect(get).toHaveBeenCalledTimes(3)
  })
})

describe('sleep', () => {
  it('waits and then continues', async () => {
    await expect(sleep(1)).resolves.toBeUndefined()
  })
})

describe('live runs and ideas', () => {
  it('lists runs and ideas from the backend', async () => {
    const fetchMock = reply(true, 200, [])
    vi.stubGlobal('fetch', fetchMock)
    await liveAlgo.listRuns()
    await liveAlgo.listRecommendations({ status: 'new' })
    await liveAlgo.listRecommendations()
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/runs', '/api/recommendations?status=new', '/api/recommendations'])
  })
  it('starts a run and waits for it to finish', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 202, json: () => Promise.resolve(run('running')) })
      .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(run('done')) })
    vi.stubGlobal('fetch', fetchMock)
    expect((await liveAlgo.startRun('on_demand')).status).toBe('done')
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/runs', '/api/runs/r1'])
  })
  it('does not wait when the answer is already final', async () => {
    const fetchMock = reply(true, 202, run('done'))
    vi.stubGlobal('fetch', fetchMock)
    await liveAlgo.startRun('dry_run')
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})

describe('live screener', () => {
  const state = (running: boolean) => ({ running, error: null, screen: null })
  it('reads the latest screen', async () => {
    const fetchMock = reply(true, 200, state(false))
    vi.stubGlobal('fetch', fetchMock)
    expect(await liveScreen.getScreen()).toEqual(state(false))
    expect(fetchMock.mock.calls[0]![0]).toBe('/api/screens/latest')
  })
  it('starts a screen and waits until it is no longer running', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 202, json: () => Promise.resolve(state(true)) })
      .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(state(false)) })
    vi.stubGlobal('fetch', fetchMock)
    expect((await liveScreen.startScreen()).running).toBe(false)
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/screens', '/api/screens/latest'])
  })
  it('does not wait when the screen was not started', async () => {
    const fetchMock = reply(true, 202, state(false))
    vi.stubGlobal('fetch', fetchMock)
    await liveScreen.startScreen()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})

describe('waitUntil', () => {
  it('uses the real pause and the default number of tries when none are given', async () => {
    const get = vi.fn().mockResolvedValue(1)
    expect(await waitUntil(get, () => true)).toBe(1)
    expect(get).toHaveBeenCalledOnce()
  })
})
