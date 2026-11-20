import { act, render, renderHook, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PageNote } from '../components/PageNote'
import { SortTh } from '../components/SortTh'
import { nextSort, sortRows, useSort } from './sort'

const ROWS = [{ n: 'Beta', v: 2 }, { n: 'alpha', v: 10 }, { n: 'Gamma', v: 1 }]
const value = (row: (typeof ROWS)[number], key: 'n' | 'v') => row[key]

describe('sorting', () => {
  it('reverses the same column and starts a new one by its kind', () => {
    expect(nextSort({ key: 'a', dir: 'asc' }, 'a', false)).toEqual({ key: 'a', dir: 'desc' })
    expect(nextSort({ key: 'a', dir: 'desc' }, 'a', true)).toEqual({ key: 'a', dir: 'asc' })
    expect(nextSort({ key: 'a', dir: 'asc' }, 'b', true)).toEqual({ key: 'b', dir: 'desc' })
    expect(nextSort({ key: 'a', dir: 'asc' }, 'b', false)).toEqual({ key: 'b', dir: 'asc' })
  })
  it('sorts numbers by size and words by alphabet, without changing the input', () => {
    expect(sortRows(ROWS, { key: 'v', dir: 'desc' }, value).map((r) => r.v)).toEqual([10, 2, 1])
    expect(sortRows(ROWS, { key: 'v', dir: 'asc' }, value).map((r) => r.v)).toEqual([1, 2, 10])
    expect(sortRows(ROWS, { key: 'n', dir: 'asc' }, value).map((r) => r.n)).toEqual(['alpha', 'Beta', 'Gamma'])
    expect(ROWS[0]!.n).toBe('Beta')
  })
  it('keeps the chosen column in a hook', () => {
    const { result } = renderHook(() => useSort<'n' | 'v'>({ key: 'v', dir: 'desc' }))
    act(() => result.current[1]('n', false))
    expect(result.current[0]).toEqual({ key: 'n', dir: 'asc' })
  })
})

describe('SortTh', () => {
  const show = (column: 'n' | 'v', numeric: boolean, onSort = vi.fn()) => {
    render(<table><thead><tr><SortTh label="Value" column={column} sort={{ key: 'v', dir: 'desc' }} onSort={onSort} numeric={numeric} /></tr></thead></table>)
    return onSort
  }
  it('marks the sorted column and asks to sort when pressed', async () => {
    const onSort = show('v', true)
    expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'descending')
    expect(screen.getByRole('columnheader')).toHaveClass('right')
    await userEvent.click(screen.getByRole('button', { name: /Value/ }))
    expect(onSort).toHaveBeenCalledWith('v', true)
  })
  it('shows an unsorted column as such', () => {
    show('n', false)
    expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'none')
    expect(screen.getByRole('columnheader')).not.toHaveClass('right')
  })
  it('shows an ascending arrow', () => {
    render(<table><thead><tr><SortTh label="Name" column="n" sort={{ key: 'n', dir: 'asc' }} onSort={vi.fn()} /></tr></thead></table>)
    expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'ascending')
  })
})

describe('PageNote', () => {
  it('lists the lines', () => {
    render(<PageNote lines={['What it does.', 'How fresh it is.']} />)
    expect(screen.getByRole('list', { name: 'About this page' })).toHaveTextContent('What it does.How fresh it is.')
  })
})
