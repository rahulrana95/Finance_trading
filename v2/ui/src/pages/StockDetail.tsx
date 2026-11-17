import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import type { StockStatus } from '../api/types'
import { Card, Meter, NeedsList, Pill, State } from '../components/ui'
import { HARD_EXIT_PCT, STOCK_STATUS_KIND, STOCK_STATUS_LABEL } from '../constants'
import { linePath, scaleY } from '../lib/chart'
import { levelPrice } from '../api/mock/engine'
import { pct, price } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { zoneLabel } from './Stocks'

const LEVELS = [10, 20, 30]

function Spark({ values, lines }: { values: number[]; lines: number[] }) {
  const all = [...values, ...lines]
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const y = (v: number) => scaleY(v, lo, hi, 200)
  return (
    <svg className="chart" role="img" aria-label="Closing price over the last year with the sell target and buy levels" viewBox="0 0 800 200" preserveAspectRatio="none">
      {lines.map((v, i) => (
        <line key={v} x1="0" x2="800" y1={y(v)} y2={y(v)} className={i === 0 ? 'line-target' : i === lines.length - 1 ? 'line-exit' : 'line-level'} vectorEffect="non-scaling-stroke" />
      ))}
      <path d={linePath(values, lo, hi, 800, 200)} className="line-price" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export function StockDetail() {
  const { symbol = '' } = useParams()
  const { data: s, error, loading, reload } = useAsync(() => api.getStock(symbol), [symbol])
  async function setStatus(status: StockStatus) {
    await api.setStockStatus(symbol, status)
    reload()
  }
  return (
    <State loading={loading} error={error}>
      {s && (
        <>
          <Link to="/stocks">← All stocks</Link>
          <header className="page-head">
            <div>
              <h1>{s.name}</h1>
              <p className="muted">{s.industry} · {s.zone > 0 ? <Pill kind="accent">{zoneLabel(s)}</Pill> : zoneLabel(s)}</p>
            </div>
            <div className="right">
              <div className="big num">{price(s.lastPrice)}</div>
              <div className="muted">{pct(s.belowHighPct)} below its 6-month high · close on {s.priceAsOf}</div>
            </div>
          </header>
          <div className="grid two">
            <Card title="Price and buy levels" aside={<span className="muted small">Last 12 months</span>}>
              <Spark values={s.history} lines={[s.referenceHigh, ...LEVELS.map((l) => levelPrice(s.referenceHigh, l)), levelPrice(s.referenceHigh, HARD_EXIT_PCT)]} />
              <dl className="rows">
                <div><dt>Sell target (6-month high)</dt><dd className="num">{price(s.referenceHigh)}</dd></div>
                {LEVELS.map((l, i) => (
                  <div key={l}><dt>Buy step {i + 1} · {l}% below</dt><dd className="num">{price(levelPrice(s.referenceHigh, l))}</dd></div>
                ))}
                <div className="loss"><dt>Exit and stop · {HARD_EXIT_PCT}% below</dt><dd className="num">{price(levelPrice(s.referenceHigh, HARD_EXIT_PCT))}</dd></div>
              </dl>
            </Card>
            <Card title="Evidence score" aside={<span className="big num">{s.scores.evidence}</span>}>
              <p className="muted small">How much evidence supports this stock, from 0 to 100. It is not a chance of profit.</p>
              {([['Recovery from falls', s.scores.stability], ['Business figures', s.scores.financial], ['Data quality', s.scores.dataQuality]] as const).map(([label, value]) => (
                <div key={label} className="part"><span>{label}</span><span className="num strong">{value}</span><Meter value={value} label={label} /></div>
              ))}
              <h3>Needs data</h3>
              <NeedsList needs={s.needs} />
            </Card>
          </div>
          <div className="grid two">
            <Card title="Recovery history since 2016">
              <dl className="rows">
                <div><dt>Falls of 10% or more</dt><dd className="num">{s.falls10}</dd></div>
                <div><dt>Back at the old high within a year</dt><dd className="num">{pct(s.recovered12mPct, 0)}</dd></div>
                <div><dt>Longest recovery</dt><dd className="num">{s.longestRecoveryDays} trading days</dd></div>
                <div><dt>Deepest fall</dt><dd className="num">{pct(Math.abs(s.maxDrawdownPct), 0)}</dd></div>
              </dl>
            </Card>
            <Card title="Business check" aside={<Pill kind={s.business.durability === 'Strong' ? 'good' : 'warn'}>{s.business.durability}</Pill>}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Year to March</th><th className="right">{s.business.revenueLabel} (₹ crore)</th><th className="right">Net profit (₹ crore)</th></tr></thead>
                  <tbody>
                    {s.financials.map((f) => (
                      <tr key={f.period}>
                        <td>{f.period}</td>
                        <td className="right num">{f.revenue?.toLocaleString('en-IN') ?? 'Needs data'}</td>
                        <td className="right num">{f.netProfit?.toLocaleString('en-IN') ?? 'Needs data'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p><span className="strong">Effect of AI:</span> {s.business.aiImpact}</p>
              <p className="note"><span className="strong">Watch:</span> {s.business.watch}</p>
            </Card>
          </div>
          <Card title="Your decision" aside={<Pill kind={STOCK_STATUS_KIND[s.status]}>{STOCK_STATUS_LABEL[s.status]}</Pill>}>
            <p className="muted">Only approved stocks get buy ideas.</p>
            <div className="actions">
              <button type="button" className="button primary" disabled={s.status === 'approved'} onClick={() => setStatus('approved')}>Approve</button>
              <button type="button" className="button" disabled={s.status === 'watching'} onClick={() => setStatus('watching')}>Keep watching</button>
              <button type="button" className="button" disabled={s.status === 'rejected'} onClick={() => setStatus('rejected')}>Reject</button>
            </div>
          </Card>
        </>
      )}
    </State>
  )
}
