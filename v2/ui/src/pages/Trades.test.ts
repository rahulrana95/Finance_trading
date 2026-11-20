import { describe, expect, it } from 'vitest'
import type { Position } from '../api/types'
import { tradeValue } from './Trades'

describe('trade columns', () => {
  it('sorts by the value shown in the column', () => {
    const position: Position = { id: 'p1', symbol: 'TITAN', name: 'Titan', mode: 'paper', instrument: 'cash', quantity: 10, avgPrice: 100, lastPrice: 110, charges: 1, unrealised: 100, openedAt: '' }
    expect(tradeValue(position, 'name')).toBe('Titan')
    expect(tradeValue(position, 'unrealised')).toBe(100)
  })
})
