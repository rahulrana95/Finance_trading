import { render, renderHook, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useAuth } from '../auth/AuthContext'
import { NeedsList } from './ui'

describe('NeedsList', () => {
  it('lists what is missing', () => {
    render(<NeedsList needs={['Promoter pledge', 'Futures lot size']} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })
  it('says so when nothing is missing', () => {
    render(<NeedsList needs={[]} />)
    expect(screen.getByText('Nothing missing.')).toBeInTheDocument()
  })
})

describe('useAuth', () => {
  it('refuses to work outside its provider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used inside AuthProvider')
  })
})
