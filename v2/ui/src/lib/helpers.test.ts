import { describe, expect, it } from 'vitest'
import { linePath, scaleY } from './chart'
import { messageOf } from './errors'
import { needsSummary } from './format'
import { readJson, remove, writeJson } from './storage'

const blocked = {
  getItem: () => { throw new Error('blocked') },
  setItem: () => { throw new Error('blocked') },
  removeItem: () => { throw new Error('blocked') },
} as unknown as Storage

describe('messageOf', () => {
  it('uses the error message', () => expect(messageOf(new Error('boom'))).toBe('boom'))
  it('falls back for anything else', () => {
    expect(messageOf('text')).toBe('Something went wrong.')
    expect(messageOf(null, 'custom')).toBe('custom')
  })
})

describe('storage', () => {
  it('writes, reads and removes JSON', () => {
    writeJson('k', { a: 1 })
    expect(readJson<{ a: number }>('k')).toEqual({ a: 1 })
    remove('k')
    expect(readJson('k')).toBeNull()
  })
  it('returns null for broken JSON', () => {
    sessionStorage.setItem('bad', '{not json')
    expect(readJson('bad')).toBeNull()
  })
  it('never throws when storage is blocked', () => {
    expect(readJson('k', blocked)).toBeNull()
    expect(() => writeJson('k', 1, blocked)).not.toThrow()
    expect(() => remove('k', blocked)).not.toThrow()
  })
})

describe('chart', () => {
  it('scales between the padded top and bottom', () => {
    expect(scaleY(0, 0, 100, 200)).toBe(190)
    expect(scaleY(100, 0, 100, 200)).toBe(10)
  })
  it('centres a flat series', () => expect(scaleY(5, 5, 5, 200)).toBe(100))
  it('draws a path across the width', () => expect(linePath([0, 100], 0, 100, 800, 200)).toBe('M0.0 190.0 L800.0 10.0'))
  it('handles a single point', () => expect(linePath([5], 5, 5, 800, 200)).toBe('M0.0 100.0'))
})

describe('needsSummary', () => {
  it('counts in words', () => expect([0, 1, 3].map(needsSummary)).toEqual(['Complete', '1 item', '3 items']))
})
