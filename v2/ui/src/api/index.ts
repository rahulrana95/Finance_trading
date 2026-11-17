import type { Api } from './types'
import { LIVE_MODE, MOCK_DELAY_MS } from '../constants'
import { liveStocks } from './http'
import { createMockApi, type MockOptions } from './mock/mockApi'

/** Tests use a fixed clock and no delay; the running app stamps runs and trades with the real time. */
export const mockOptions = (test: boolean): MockOptions => (test ? { delayMs: 0 } : { delayMs: MOCK_DELAY_MS, now: () => new Date() })

/** In live mode the routes the backend already serves replace their mock versions. */
export const composeApi = (mock: Api, live: boolean): Api => (live ? { ...mock, ...liveStocks } : mock)

export const LIVE = import.meta.env.VITE_API_MODE === LIVE_MODE
const make = (): Api => composeApi(createMockApi(mockOptions(import.meta.env.MODE === 'test')), LIVE)

// The interface talks to this object only. When the backend routes exist, an HTTP client
// with the same shape replaces the mock here, one method at a time.
export let api: Api = make()
export const USING_MOCK = true // sign-in is still the demo account

/** Tests call this to start each case from the seeded state. */
export function resetMockApi(): void {
  api = make()
}
