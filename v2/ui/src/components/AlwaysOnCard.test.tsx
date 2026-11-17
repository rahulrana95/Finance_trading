import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AlwaysOnCard } from './AlwaysOnCard'

describe('AlwaysOnCard', () => {
  it('shows a switch for the sample schedule', async () => {
    const onToggle = vi.fn()
    render(<AlwaysOnCard server={false} on onToggle={onToggle} />)
    expect(screen.getByText('Running')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('switch', { name: 'Always on' }))
    expect(onToggle).toHaveBeenCalledOnce()
  })
  it('says when the sample schedule is paused', () => {
    render(<AlwaysOnCard server={false} on={false} onToggle={vi.fn()} />)
    expect(screen.getByText(/Paused/)).toBeInTheDocument()
    expect(screen.getByRole('switch')).not.toBeChecked()
  })
  it('has no switch when the schedule runs on the server', () => {
    render(<AlwaysOnCard server on={false} onToggle={vi.fn()} />)
    expect(screen.queryByRole('switch')).toBeNull()
    expect(screen.getByText(/Running on the server/)).toBeInTheDocument()
  })
})
