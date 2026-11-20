import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { ModeFilter, Position } from '../api/types'
import { PageNote } from '../components/PageNote'
import { SortTh } from '../components/SortTh'
import { Card, ModeTabs, Money, Pill, State } from '../components/ui'
import { INSTRUMENT_LABEL, MODE_LABEL, PAGE_NOTES, ROUTES, SIDE_LABEL } from '../constants'
import { dateTime, price, rupees } from '../lib/format'
import { sortRows, useSort, type SortValue } from '../lib/sort'
import { useAsync } from '../lib/useAsync'

type TradeColumn = 'name' | 'quantity' | 'avgPrice' | 'lastPrice' | 'unrealised'
export const tradeValue = (position: Position, column: TradeColumn): SortValue => position[column]

export function Trades() {
  const [mode, setMode] = useState<ModeFilter>('paper')
  const open = useAsync(() => api.openTrades(mode), [mode])
  const log = useAsync(() => api.tradeLog(mode), [mode])
  const pnl = useAsync(() => api.pnl(mode), [mode])
  const [sort, onSort] = useSort<TradeColumn>({ key: 'unrealised', dir: 'desc' })
  const head = { sort, onSort }
  const positions = sortRows(open.data ?? [], sort, tradeValue)
  return (
    <>
      <header className="page-head">
        <div>
          <h1>Trades</h1>
          <p className="muted">Open positions and profit or loss, priced from the latest market data.</p>
        </div>
        <ModeTabs value={mode} onChange={setMode} />
      </header>
      <PageNote lines={PAGE_NOTES.trades} />
      <div className="grid four">
        <Card><span className="muted">Invested</span><span className="big num">{rupees(pnl.data?.invested ?? 0)}</span></Card>
        <Card><span className="muted">Open profit or loss</span><span className="big"><Money value={pnl.data?.unrealised ?? 0} /></span></Card>
        <Card><span className="muted">Closed profit or loss</span><span className="big"><Money value={pnl.data?.realised ?? 0} /></span></Card>
        <Card><span className="muted">Charges paid</span><span className="big num">{rupees(pnl.data?.charges ?? 0)}</span></Card>
      </div>
      <Card title="Open trades">
        <State loading={open.loading} error={open.error} empty={!open.data?.length && (mode === 'real' ? 'No real trades. Real trading is locked.' : 'No open trades yet.')}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <SortTh label="Stock" column="name" {...head} /><th>Type</th><th>Holding</th>
                  <SortTh label="Quantity" column="quantity" numeric {...head} /><SortTh label="Average price" column="avgPrice" numeric {...head} />
                  <SortTh label="Last price" column="lastPrice" numeric {...head} /><SortTh label="Profit or loss" column="unrealised" numeric {...head} />
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.id}>
                    <td><Link to={`/stocks/${p.symbol}`} className="strong">{p.name}</Link></td>
                    <td><Pill kind="warn">{MODE_LABEL[p.mode]}</Pill></td>
                    <td>{INSTRUMENT_LABEL[p.instrument]}</td>
                    <td className="right num">{p.quantity}</td>
                    <td className="right num">{price(p.avgPrice)}</td>
                    <td className="right num">{price(p.lastPrice)}</td>
                    <td className="right"><Money value={p.unrealised} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </State>
        {!open.data?.length && mode !== 'real' && <p><Link to={ROUTES.ideas}>See ideas waiting for you</Link></p>}
      </Card>
      <Card title="Trade log">
        <State loading={log.loading} error={log.error} empty={!log.data?.length && 'Nothing logged yet.'}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>When</th><th>Stock</th><th>Type</th><th>Action</th><th className="right">Quantity</th><th className="right">Price</th><th className="right">Charges</th><th>Price from</th></tr>
              </thead>
              <tbody>
                {log.data?.map((t) => (
                  <tr key={t.id}>
                    <td>{dateTime(t.at)}</td><td>{t.symbol}</td><td>{MODE_LABEL[t.mode]}</td>
                    <td>{SIDE_LABEL[t.side]} {INSTRUMENT_LABEL[t.instrument].toLowerCase()}</td>
                    <td className="right num">{t.quantity}</td><td className="right num">{price(t.price)}</td><td className="right num">{price(t.charges)}</td><td className="small">{t.source}</td>
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
