import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DecisionCard } from './DecisionCard'

describe('DecisionCard', () => {
  it('offers the other two choices and reports the one picked', async () => {
    const onChange = vi.fn()
    render(<DecisionCard status="watching" readOnly={false} onChange={onChange} />)
    expect(screen.getByRole('button', { name: 'Keep watching' })).toBeDisabled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Approve' }))
    expect(onChange).toHaveBeenCalledWith('approved')
  })
  it('shows a note instead of buttons while decisions cannot be saved', () => {
    render(<DecisionCard status="approved" readOnly onChange={vi.fn()} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.getByText(/arrives with sign-in/)).toBeInTheDocument()
    expect(screen.getByText('Approved')).toBeInTheDocument()
  })
})
