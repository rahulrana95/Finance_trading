import type { SortState } from '../lib/sort'

interface Props<K extends string> {
  label: string
  column: K
  sort: SortState<K>
  onSort: (key: K, numeric: boolean) => void
  /** Numbers are right-aligned and start largest first. */
  numeric?: boolean
}

const ARROW = { asc: '▲', desc: '▼' } as const
const ARIA = { asc: 'ascending', desc: 'descending' } as const

/** A column heading that sorts the table when pressed. */
export function SortTh<K extends string>({ label, column, sort, onSort, numeric = false }: Props<K>) {
  const active = sort.key === column
  return (
    <th className={numeric ? 'right' : undefined} aria-sort={active ? ARIA[sort.dir] : 'none'}>
      <button type="button" className={active ? 'sort-button on' : 'sort-button'} onClick={() => onSort(column, numeric)}>
        {label} <span aria-hidden="true">{active ? ARROW[sort.dir] : '↕'}</span>
      </button>
    </th>
  )
}
