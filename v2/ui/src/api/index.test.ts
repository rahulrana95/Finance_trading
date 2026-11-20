import { describe, expect, it } from 'vitest'
import { composeApi, mockOptions } from './index'
import { liveAlgo, liveScreen, liveStocks } from './http'
import { createMockApi } from './mock/mockApi'

describe('composeApi', () => {
  const mock = createMockApi({ delayMs: 0 })
  it('keeps the mock untouched when not live', () => expect(composeApi(mock, false)).toBe(mock))
  it('swaps in the live stock, run and idea routes and keeps the rest', () => {
    const api = composeApi(mock, true)
    expect(api.listStocks).toBe(liveStocks.listStocks)
    expect(api.getStock).toBe(liveStocks.getStock)
    expect(api.listRuns).toBe(liveAlgo.listRuns)
    expect(api.startRun).toBe(liveAlgo.startRun)
    expect(api.listRecommendations).toBe(liveAlgo.listRecommendations)
    expect(api.getScreen).toBe(liveScreen.getScreen)
    expect(api.startScreen).toBe(liveScreen.startScreen)
    expect(api.approve).toBe(mock.approve)
  })
})

describe('mock options', () => {
  it('uses no delay and the fixed clock in tests', () => expect(mockOptions(true)).toEqual({ delayMs: 0 }))
  it('uses a short delay and the real clock when running', () => {
    const options = mockOptions(false)
    expect(options.delayMs).toBe(150)
    expect(Math.abs(options.now!().getTime() - Date.now())).toBeLessThan(1000)
  })
})
