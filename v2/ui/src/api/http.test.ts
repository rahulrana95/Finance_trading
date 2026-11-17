import { afterEach, describe, expect, it, vi } from 'vitest'
import { getJson, liveStocks } from './http'

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
