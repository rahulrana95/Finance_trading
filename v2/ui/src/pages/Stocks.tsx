import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { Stock, StockStatus } from '../api/types'
import { PageNote } from '../components/PageNote'
import { SortTh } from '../components/SortTh'
import { Card, Meter, Pill, State } from '../components/ui'
import { PAGE_NOTES, PRICES_NOT_LIVE, STOCK_STATUS_KIND, STOCK_STATUS_LABEL } from '../constants'
import { day, needsSummary, pct, priceOrNeeds } from '../lib/format'
import { sortRows, useSort, type SortValue } from '../lib/sort'
import { useAsync } from '../lib/useAsync'

type StockColumn = 'name' | 'status' | 'price' | 'below' | 'zone' | 'evidence' | 'needs'

export function stockValue(stock: Stock, column: StockColumn): SortValue {
  const values: Record<StockColumn, SortValue> = {
    name: stock.name, status: stock.status, price: stock.lastPrice, below: stock.belowHighPct, zone: stock.zone, evidence: stock.scores.evidence, needs: stock.needs.length,
  }
  return values[column]
}

/** The newest price date in the table, or nothing when no price arrived. */
export const latestDay = (stocks: Stock[]): string | undefined => stocks.map((s) => s.priceAsOf).filter(Boolean).sort().at(-1)

export function zoneLabel(stock: Stock): string {
  return stock.zone > 0 ? `Buy zone ${stock.zone}` : 'Not in a buy zone'
}

export function Stocks() {
  const { data, error, loading } = useAsync(() => api.listStocks(), [])
  const [status, setStatus] = useState<StockStatus | 'all'>('all')
  const [onlyZone, setOnlyZone] = useState(false)
  const [sort, onSort] = useSort<StockColumn>({ key: 'evidence', dir: 'desc' })

  const rows = useMemo(
    () => sortRows((data ?? []).filter((s) => (status === 'all' || s.status === status) && (!onlyZone || s.zone > 0)), sort, stockValue),
    [data, status, onlyZone, sort],
  )
  const priced = latestDay(data ?? [])
  const head = { sort, onSort }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Stocks</h1>
          <p className="muted">Stocks that have recovered from falls and passed a business check. Scores describe the past.</p>
        </div>
      </header>
      <PageNote lines={[...PAGE_NOTES.stocks, `${PRICES_NOT_LIVE}${priced ? ` Latest price: ${day(priced)}.` : ''} They refresh every 30 minutes.`]} />
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
                  <SortTh label="Stock" column="name" {...head} />
                  <SortTh label="Status" column="status" {...head} />
                  <SortTh label="Price" column="price" numeric {...head} />
                  <SortTh label="Below 6-month high" column="below" numeric {...head} />
                  <SortTh label="Zone" column="zone" numeric {...head} />
                  <SortTh label="Evidence score" column="evidence" numeric {...head} />
                  <SortTh label="Needs data" column="needs" numeric {...head} />
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.symbol}>
                    <td>
                      <Link to={`/stocks/${s.symbol}`} className="strong">{s.name}</Link>
                      <div className="muted small">{s.industry}</div>
                    </td>
                    <td><Pill kind={STOCK_STATUS_KIND[s.status]}>{STOCK_STATUS_LABEL[s.status]}</Pill></td>
                    <td className="right num">{priceOrNeeds(s)}</td>
                    <td className="right num">{pct(s.belowHighPct)}</td>
                    <td>{s.zone > 0 ? <Pill kind="accent">{zoneLabel(s)}</Pill> : <span className="muted">{zoneLabel(s)}</span>}</td>
                    <td>
                      <div className="score"><span className="num strong">{s.scores.evidence}</span><Meter value={s.scores.evidence} label={`${s.name} evidence score`} /></div>
                    </td>
                    <td className="small">{needsSummary(s.needs.length)}</td>
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
