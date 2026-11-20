import { useMemo, useState } from 'react'
import { api } from '../api'
import type { Evidence, Odds, Screen, ScreenRow } from '../api/types'
import { PageNote } from '../components/PageNote'
import { SortTh } from '../components/SortTh'
import { Card, Pill, State } from '../components/ui'
import { CONFIDENCE_KIND, CONFIDENCE_LABEL, MARKET_KIND, MARKET_LABEL, MARKET_ROW_LABEL, MARKET_TEXT, NO_HIGH_TEXT, NOT_EVIDENCE_TEXT, PAGE_NOTES, PRICES_NOT_LIVE, SCREEN_CAVEAT } from '../constants'
import { messageOf } from '../lib/errors'
import { dateTime, day, pct, price } from '../lib/format'
import { columnValue, countBy, demergerNote, oddsFor, ownRecord, pickRows, type ScreenColumn } from '../lib/screen'
import { sortRows, useSort } from '../lib/sort'
import { useAsync } from '../lib/useAsync'

const chance = (value: number | undefined): string => (value === undefined ? '–' : pct(value, 0))

export function EvidenceList({ items }: { items: Evidence[] }) {
  return (
    <ul className="evidence">
      {items.map((e) => (
        <li key={e.label}>
          <span className={e.met ? 'met' : 'unmet'} aria-label={e.met ? 'Yes' : 'No'}>{e.met ? '✓' : '✗'}</span>
          <span><span className="strong">{e.label}.</span> {e.detail}</span>
        </li>
      ))}
    </ul>
  )
}

function OddsTable({ odds }: { odds: Odds[] }) {
  return (
    <div className="table-wrap">
      <table aria-label="What happened after past falls">
        <thead>
          <tr>
            <th>Stock fell at least</th><th>Market that day</th><th className="right">Past falls</th>
            <th className="right">Reached +10% in 6 months</th><th className="right">Reached +20% in 6 months</th><th className="right">Higher after 6 months</th>
            <th className="right">Reached +30% in a year</th><th className="right">Higher after a year</th><th className="right">Fell 20% more first</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((o) => (
            <tr key={`${o.level}-${o.market}`} className={o.market === 'deep' ? 'row-next' : undefined}>
              <td className="strong">{o.level}%</td>
              <td>{MARKET_ROW_LABEL[o.market]}</td>
              <td className="right num">{o.events}</td>
              <td className="right num">{chance(o.gain10In6mPct)}</td>
              <td className="right num">{chance(o.gain20In6mPct)}</td>
              <td className="right num strong">{chance(o.higherAfter6mPct)}</td>
              <td className="right num">{chance(o.gain30In12mPct)}</td>
              <td className="right num strong">{chance(o.higherAfter12mPct)}</td>
              <td className="right num">{chance(o.fellFurtherPct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Picks({ screen }: { screen: Screen }) {
  const high = screen.rows.filter((r) => r.confidence === 'high')
  return (
    <Card title={`High-confidence buys today (${high.length})`}>
      {high.length === 0 ? (
        <>
          <p className="strong">None today. Nifty is {pct(screen.marketBelowPct)} below its 1-year high.</p>
          <p>{NO_HIGH_TEXT}</p>
          <p className="muted">Today: {countBy(screen.rows, 'medium')} stocks at medium confidence and {countBy(screen.rows, 'low')} at low.</p>
        </>
      ) : (
        high.map((r) => {
          const odds = oddsFor(screen, r.level)
          return (
            <div className="pick" key={r.symbol} aria-label={`Pick ${r.name}`} role="group">
              <p><span className="strong">{r.name}</span> · {r.industry} · {price(r.lastPrice)} · {pct(r.belowPct)} below its 1-year high</p>
              <p>After similar falls: {chance(odds?.higherAfter6mPct)} higher after 6 months, {chance(odds?.higherAfter12mPct)} after a year; {chance(odds?.fellFurtherPct)} fell another 20% first.</p>
              <EvidenceList items={r.evidence} />
            </div>
          )
        })
      )}
      <p className="muted small">{NOT_EVIDENCE_TEXT}</p>
    </Card>
  )
}

function Row({ row, screen }: { row: ScreenRow; screen: Screen }) {
  const [open, setOpen] = useState(false)
  const odds = oddsFor(screen, row.level)
  const note = demergerNote(row)
  return (
    <>
      <tr>
        <td>
          <span className="strong">{row.name}</span>
          {note && <div className="small loss">{note}</div>}
          <div><button type="button" className="link-button" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Hide evidence' : 'Evidence'}</button></div>
        </td>
        <td><Pill kind={CONFIDENCE_KIND[row.confidence]}>{CONFIDENCE_LABEL[row.confidence]}</Pill></td>
        <td>{row.industry}</td>
        <td className="right num">{price(row.lastPrice)}</td>
        <td className="right num">{pct(row.belowPct)}</td>
        <td className="right num strong">{chance(odds?.higherAfter6mPct)}</td>
        <td className="right num">{chance(odds?.gain10In6mPct)}</td>
        <td className="right num">{chance(odds?.gain30In12mPct)}</td>
        <td className="right num">{chance(odds?.fellFurtherPct)}</td>
        <td>{ownRecord(row)}</td>
      </tr>
      {open && (
        <tr className="evidence-row">
          <td colSpan={10} aria-label={`Evidence for ${row.name}`}><EvidenceList items={row.evidence} /></td>
        </tr>
      )}
    </>
  )
}

function Fallen({ screen }: { screen: Screen }) {
  const [minLevel, setMinLevel] = useState(20)
  const [search, setSearch] = useState('')
  const [sort, onSort] = useSort<ScreenColumn>({ key: 'confidence', dir: 'desc' })
  const rows = useMemo(() => sortRows(pickRows(screen.rows, minLevel, search), sort, columnValue), [screen.rows, minLevel, search, sort])
  const head = { sort, onSort }
  return (
    <Card title={`Stocks in a deep fall today (${rows.length})`}>
      <div className="filters">
        <label>Fell at least
          <select value={minLevel} onChange={(e) => setMinLevel(Number(e.target.value))}>
            <option value={20}>20%</option><option value={25}>25%</option><option value={30}>30%</option><option value={40}>40%</option>
          </select>
        </label>
        <label>Find
          <input type="search" value={search} placeholder="Name or industry" onChange={(e) => setSearch(e.target.value)} />
        </label>
      </div>
      <p className="muted small">Press a column heading to sort; press it again to reverse.</p>
      <State loading={false} error={undefined} empty={!rows.length && 'No stock matches.'}>
        <div className="table-wrap">
          <table aria-label="Stocks in a deep fall">
            <thead>
              <tr>
                <SortTh label="Stock" column="name" {...head} />
                <SortTh label="Confidence" column="confidence" numeric {...head} />
                <SortTh label="Industry" column="industry" {...head} />
                <SortTh label="Price" column="price" numeric {...head} />
                <SortTh label="Below 1-year high" column="below" numeric {...head} />
                <th className="right">Higher after 6 months</th><th className="right">Reached +10% in 6 months</th><th className="right">Reached +30% in a year</th>
                <th className="right">Fell 20% more first</th>
                <SortTh label="Its own record" column="record" numeric {...head} />
              </tr>
            </thead>
            <tbody>{rows.map((r) => <Row key={r.symbol} row={r} screen={screen} />)}</tbody>
          </table>
        </div>
      </State>
    </Card>
  )
}

/** The newest price date among the fallen stocks, or nothing when the list is empty. */
export const latestPriceDay = (screen: Screen): string | undefined => screen.rows.map((r) => r.priceAsOf).sort().at(-1)

export function Screener() {
  const { data, error, loading, reload } = useAsync(() => api.getScreen(), [])
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string>()
  const screen = data?.screen
  const priced = screen && latestPriceDay(screen)

  async function screenNow() {
    setBusy(true)
    setFailure(undefined)
    try {
      await api.startScreen()
      reload()
    } catch (e) {
      setFailure(messageOf(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Screener</h1>
          <p className="muted">Which fallen stocks are worth buying, and how sure the history is.</p>
        </div>
        <button type="button" className="button primary" disabled={busy || data?.running} onClick={screenNow}>
          {busy || data?.running ? 'Screening…' : 'Screen now'}
        </button>
      </header>
      <PageNote lines={[...PAGE_NOTES.screener, `${PRICES_NOT_LIVE}${priced ? ` Latest price: ${day(priced)}.` : ''} It refreshes at 18:30 on weekdays and when you press Screen now.`]} />
      {(failure ?? data?.error) && <p className="error" role="alert">{failure ?? data?.error}</p>}
      <State loading={loading} error={error} empty={!screen && 'No screen yet. Press Screen now; it takes under a minute.'}>
        {screen && (
          <>
            <Card title="Market today" aside={<Pill kind={MARKET_KIND[screen.market]}>{MARKET_LABEL[screen.market]}</Pill>}>
              <p>Nifty is {pct(screen.marketBelowPct)} below its 1-year high. {MARKET_TEXT[screen.market]}</p>
              <p className="muted small">Screened {dateTime(screen.createdAt)} · prices for {screen.priced} of {screen.universe} stocks</p>
            </Card>
            <Picks screen={screen} />
            <Fallen screen={screen} />
            <Card title="What happened after past falls">
              <OddsTable odds={screen.odds} />
            </Card>
            <p className="muted small">{SCREEN_CAVEAT}</p>
          </>
        )}
      </State>
    </>
  )
}
