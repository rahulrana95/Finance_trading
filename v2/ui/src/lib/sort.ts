// Click-to-sort for tables: one column at a time, click again to reverse.
import { useCallback, useState } from 'react'

export type SortDir = 'asc' | 'desc'
export interface SortState<K extends string> {
  key: K
  dir: SortDir
}
export type SortValue = string | number

/** Same column: reverse. New column: words start A to Z, numbers start largest first. */
export function nextSort<K extends string>(state: SortState<K>, key: K, numeric: boolean): SortState<K> {
  if (state.key === key) return { key, dir: state.dir === 'asc' ? 'desc' : 'asc' }
  return { key, dir: numeric ? 'desc' : 'asc' }
}

export function sortRows<T, K extends string>(rows: readonly T[], state: SortState<K>, value: (row: T, key: K) => SortValue): T[] {
  const sign = state.dir === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    const x = value(a, state.key)
    const y = value(b, state.key)
    return sign * (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y)))
  })
}

export function useSort<K extends string>(initial: SortState<K>): [SortState<K>, (key: K, numeric: boolean) => void] {
  const [state, setState] = useState(initial)
  const toggle = useCallback((key: K, numeric: boolean) => setState((s) => nextSort(s, key, numeric)), [])
  return [state, toggle]
}
