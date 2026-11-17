import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { Stock, StockStatus } from '../api/types'
import { Card, Meter, Pill, State } from '../components/ui'
import { pct, price } from '../lib/format'
import { useAsync } from '../lib/useAsync'

type SortKey = 'evidence' | 'below' | 'name'
const STATUS_LABEL: Record<StockStatus, string> = { approved: 'Approved', watching: 'Watching', rejected: 'Rejected' }
const STATUS_KIND = { approved: 'good', watching: 'neutral', rejected: 'bad' } as const

export function zoneLabel(stock: Stock): string {
  return stock.zone > 0 ? `Buy zone ${stock.zone}` : 'Not in a buy zone'
}

export function Stocks() {
  const { data, error, loading } = useAsync(() => api.listStocks(), [])
  const [status, setStatus] = useState<StockStatus | 'all'>('all')
  const [onlyZone, setOnlyZone] = useState(false)
  const [sort, setSort] = useState<SortKey>('evidence')

  const rows = useMemo(() => {
    const filtered = (data ?? []).filter((s) => (status === 'all' || s.status === status) && (!onlyZone || s.zone > 0))
    return [...filtered].sort((a, b) =>
      sort === 'name' ? a.name.localeCompare(b.name) : sort === 'below' ? b.belowHighPct - a.belowHighPct : b.scores.evidence - a.scores.evidence,
    )
  }, [data, status, onlyZone, sort])

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Stocks</h1>
          <p className="muted">Stocks that have recovered from falls and passed a business check. Scores describe the past.</p>
        </div>
      </header>
      <Card>
        <div className="filters">
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value as StockStatus | 'all')}>
              <option value="all">All</option>
              <option value="approved">Approved</option>
              <option value="watching">Watching</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
          <label>
            Sort by
            <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
              <option value="evidence">Evidence score</option>
              <option value="below">Furthest below high</option>
              <option value="name">Name</option>
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={onlyZone} onChange={(e) => setOnlyZone(e.target.checked)} />
            Only stocks in a buy zone
          </label>
        </div>
        <State loading={loading} error={error} empty={!rows.length && 'No stocks match these filters.'}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Status</th>
                  <th className="right">Price</th>
                  <th className="right">Below 6-month high</th>
                  <th>Zone</th>
                  <th>Evidence score</th>
                  <th>Needs data</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.symbol}>
                    <td>
                      <Link to={`/stocks/${s.symbol}`} className="strong">{s.name}</Link>
                      <div className="muted small">{s.industry}</div>
                    </td>
                    <td><Pill kind={STATUS_KIND[s.status]}>{STATUS_LABEL[s.status]}</Pill></td>
                    <td className="right num">{price(s.lastPrice)}</td>
                    <td className="right num">{pct(s.belowHighPct)}</td>
                    <td>{s.zone > 0 ? <Pill kind="accent">{zoneLabel(s)}</Pill> : <span className="muted">{zoneLabel(s)}</span>}</td>
                    <td>
                      <div className="score"><span className="num strong">{s.scores.evidence}</span><Meter value={s.scores.evidence} label={`${s.name} evidence score`} /></div>
                    </td>
                    <td className="small">{s.needs.length ? `${s.needs.length} item${s.needs.length === 1 ? '' : 's'}` : 'Complete'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </State>
      </Card>
    </>
  )
}
