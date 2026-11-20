import { useMemo, useState } from 'react'
import { api } from '../api'
import type { Odds, Screen } from '../api/types'
import { Card, Pill, State } from '../components/ui'
import { MARKET_DOWN_TEXT, MARKET_FINE_TEXT, SCREEN_CAVEAT } from '../constants'
import { messageOf } from '../lib/errors'
import { dateTime, pct, price } from '../lib/format'
import { demergerNote, oddsFor, ownRecord, pickRows, type ScreenSort } from '../lib/screen'
import { useAsync } from '../lib/useAsync'

const chance = (value: number | undefined): string => (value === undefined ? '–' : pct(value, 0))

function OddsTable({ odds }: { odds: Odds[] }) {
  return (
    <div className="table-wrap">
      <table aria-label="What happened after past falls">
        <thead>
          <tr>
            <th>Fell at least</th><th>Market that day</th><th className="right">Past falls</th>
            <th className="right">Reached +10% in 6 months</th><th className="right">Reached +20% in 6 months</th><th className="right">Higher after 6 months</th>
            <th className="right">Reached +30% in a year</th><th className="right">Higher after a year</th><th className="right">Fell 20% more first</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((o) => (
            <tr key={`${o.level}-${o.marketDown}`} className={o.marketDown ? 'row-next' : undefined}>
              <td className="strong">{o.level}%</td>
              <td>{o.marketDown ? 'Also in a fall' : 'Not in a fall'}</td>
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

function Fallen({ screen }: { screen: Screen }) {
  const [minLevel, setMinLevel] = useState(20)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<ScreenSort>('deepest')
  const rows = useMemo(() => pickRows(screen.rows, minLevel, search, sort), [screen.rows, minLevel, search, sort])
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
        <label>Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value as ScreenSort)}>
            <option value="deepest">Furthest below high</option><option value="record">Its own record</option><option value="name">Name</option>
          </select>
        </label>
      </div>
      <State loading={false} error={undefined} empty={!rows.length && 'No stock matches.'}>
        <div className="table-wrap">
          <table aria-label="Stocks in a deep fall">
            <thead>
              <tr>
                <th>Stock</th><th>Industry</th><th className="right">Price</th><th className="right">Below 1-year high</th>
                <th className="right">Higher after 6 months</th><th className="right">Reached +10% in 6 months</th><th className="right">Reached +30% in a year</th>
                <th className="right">Fell 20% more first</th><th>Its own record</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const odds = oddsFor(screen, r.level)
                const note = demergerNote(r)
                return (
                  <tr key={r.symbol}>
                    <td><span className="strong">{r.name}</span>{note && <div className="small loss">{note}</div>}</td>
                    <td>{r.industry}</td>
                    <td className="right num">{price(r.lastPrice)}</td>
                    <td className="right num">{pct(r.belowPct)}</td>
                    <td className="right num strong">{chance(odds?.higherAfter6mPct)}</td>
                    <td className="right num">{chance(odds?.gain10In6mPct)}</td>
                    <td className="right num">{chance(odds?.gain30In12mPct)}</td>
                    <td className="right num">{chance(odds?.fellFurtherPct)}</td>
                    <td>{ownRecord(r)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </State>
    </Card>
  )
}

export function Screener() {
  const { data, error, loading, reload } = useAsync(() => api.getScreen(), [])
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string>()
  const screen = data?.screen

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
          <p className="muted">Checks about 500 stocks for deep falls and shows how similar falls turned out before.</p>
        </div>
        <button type="button" className="button primary" disabled={busy || data?.running} onClick={screenNow}>
          {busy || data?.running ? 'Screening…' : 'Screen now'}
        </button>
      </header>
      {(failure ?? data?.error) && <p className="error" role="alert">{failure ?? data?.error}</p>}
      <State loading={loading} error={error} empty={!screen && 'No screen yet. Press Screen now; it takes under a minute.'}>
        {screen && (
          <>
            <Card title="Market today" aside={<Pill kind={screen.marketDown ? 'good' : 'neutral'}>{screen.marketDown ? 'Market in a fall' : 'Market not in a fall'}</Pill>}>
              <p>Nifty is {pct(screen.marketBelowPct)} below its 1-year high. {screen.marketDown ? MARKET_DOWN_TEXT : MARKET_FINE_TEXT}</p>
              <p className="muted small">Screened {dateTime(screen.createdAt)} · prices for {screen.priced} of {screen.universe} stocks</p>
            </Card>
            <Card title="What happened after past falls">
              <OddsTable odds={screen.odds} />
            </Card>
            <Fallen screen={screen} />
            <p className="muted small">{SCREEN_CAVEAT}</p>
          </>
        )}
      </State>
    </>
  )
}
