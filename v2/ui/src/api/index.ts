import type { Api } from './types'
import { createMockApi } from './mock/mockApi'

const TEST = import.meta.env.MODE === 'test'
// Tests use a fixed clock and no delay; the running app stamps runs and trades with the real time.
const make = (): Api => createMockApi(TEST ? { delayMs: 0 } : { delayMs: 150, now: () => new Date() })

// The interface talks to this object only. When the backend routes exist, an HTTP client
// with the same shape replaces the mock here, one method at a time.
export let api: Api = make()
export const USING_MOCK = true

/** Tests call this to start each case from the seeded state. */
export function resetMockApi(): void {
  api = make()
}
