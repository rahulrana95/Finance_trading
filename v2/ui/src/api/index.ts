import type { Api } from './types'
import { MOCK_DELAY_MS } from '../constants'
import { createMockApi, type MockOptions } from './mock/mockApi'

/** Tests use a fixed clock and no delay; the running app stamps runs and trades with the real time. */
export const mockOptions = (test: boolean): MockOptions => (test ? { delayMs: 0 } : { delayMs: MOCK_DELAY_MS, now: () => new Date() })
const make = (): Api => createMockApi(mockOptions(import.meta.env.MODE === 'test'))

// The interface talks to this object only. When the backend routes exist, an HTTP client
// with the same shape replaces the mock here, one method at a time.
export let api: Api = make()
export const USING_MOCK = true

/** Tests call this to start each case from the seeded state. */
export function resetMockApi(): void {
  api = make()
}
