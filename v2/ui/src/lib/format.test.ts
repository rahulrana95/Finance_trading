import { describe, expect, it } from 'vitest'
import { dateTime, day, pct, price, rupees, signedRupees, tone } from './format'

describe('format', () => {
  it('groups rupees the Indian way', () => {
    expect(rupees(2000000)).toBe('₹20,00,000')
    expect(rupees(66666.6)).toBe('₹66,667')
  })
  it('shows prices with paise', () => expect(price(1607.9)).toBe('₹1,607.90'))
  it('marks profit and loss with a sign and an arrow, not colour alone', () => {
    expect(signedRupees(1250)).toBe('▲ +₹1,250')
    expect(signedRupees(-1250.4)).toBe('▼ −₹1,250')
    expect(signedRupees(0)).toBe('₹0')
  })
  it('formats percentages', () => {
    expect(pct(15.74)).toBe('15.7%')
    expect(pct(85, 0)).toBe('85%')
  })
  it('names the tone', () => {
    expect([tone(1), tone(-1), tone(0)]).toEqual(['gain', 'loss', 'flat'])
  })
  it('formats dates in India time', () => {
    expect(dateTime('2026-11-17T15:25:00+05:30')).toContain('15:25')
    expect(day('2026-11-17T15:25:00+05:30')).toContain('2026')
  })
})
