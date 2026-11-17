import { describe, expect, it } from 'vitest'
import { mockOptions } from './index'

describe('mock options', () => {
  it('uses no delay and the fixed clock in tests', () => expect(mockOptions(true)).toEqual({ delayMs: 0 }))
  it('uses a short delay and the real clock when running', () => {
    const options = mockOptions(false)
    expect(options.delayMs).toBe(150)
    expect(Math.abs(options.now!().getTime() - Date.now())).toBeLessThan(1000)
  })
})
