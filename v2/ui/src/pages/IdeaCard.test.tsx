import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Recommendation } from '../api/types'
import { IDEA_READ_ONLY } from '../constants'
import { IdeaCard } from './Ideas'

const rec = (status: Recommendation['status']): Recommendation => ({
  id: 'i1', symbol: 'TITAN', name: 'Titan', zone: 1, instrumentType: 'cash',
  steps: [{ step: 1, levelPct: 10, levelPrice: 90, amount: 66666, instrument: 'cash', quantity: 784, reached: true, filled: false }],
  targetPrice: 100, hardExitPrice: 60, evidenceScore: 70, reasons: ['Fell'], risks: ['Gold'], futuresNote: 'No futures.', status, createdAt: '2026-11-17T10:00:00Z',
})

const show = (status: Recommendation['status']) =>
  render(<MemoryRouter><IdeaCard rec={rec(status)} readOnly onChanged={vi.fn()} /></MemoryRouter>)

describe('IdeaCard from the server', () => {
  it('shows the plan but no approve or skip while decisions cannot be saved', () => {
    show('new')
    expect(screen.getByText(IDEA_READ_ONLY)).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('₹66,666')).toBeInTheDocument()
  })
  it('says nothing extra for an idea that has expired', () => {
    show('expired')
    expect(screen.queryByText(IDEA_READ_ONLY)).toBeNull()
    expect(screen.getByText('Expired')).toBeInTheDocument()
  })
})
