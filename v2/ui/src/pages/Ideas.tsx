import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { InstrumentType, Mode, RecStatus, Recommendation } from '../api/types'
import { Card, Meter, Pill, State } from '../components/ui'
import { price, rupees } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const TYPE_LABEL: Record<InstrumentType, string> = { cash: 'Shares', future: 'Futures', combo: 'Shares and futures' }
const STATUS_LABEL: Record<RecStatus, string> = { new: 'Waiting for you', approved: 'Approved', skipped: 'Skipped', expired: 'Expired' }

function IdeaCard({ rec, onChanged }: { rec: Recommendation; onChanged: () => void }) {
  const [mode, setMode] = useState<Mode>('paper')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const next = rec.steps.find((s) => s.reached && !s.filled)

  async function act(action: () => Promise<unknown>) {
    setBusy(true)
    setError(undefined)
    try {
      await action()
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="card idea" aria-label={`Idea for ${rec.name}`}>
      <div className="idea-head">
        <div>
          <Link to={`/stocks/${rec.symbol}`} className="idea-name">{rec.name}</Link>
          <div className="muted small">Dip ladder · buy zone {rec.zone}</div>
        </div>
        <Pill kind={rec.status === 'new' ? 'accent' : 'neutral'}>{STATUS_LABEL[rec.status]}</Pill>
        <Pill kind="good">Buy: {TYPE_LABEL[rec.instrumentType]}</Pill>
        <div className="idea-score">
          <span className="muted small">Evidence score</span>
          <span className="big num">{rec.evidenceScore}</span>
          <Meter value={rec.evidenceScore} label={`${rec.name} evidence score`} />
        </div>
      </div>
      <div className="grid two">
        <div>
          <h3>Why</h3>
          <ul>{rec.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
        <div>
          <h3>What could go wrong</h3>
          <ul>{rec.risks.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      </div>
      <h3>Plan: start small, add more only if it falls further</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Step</th><th>When</th><th>Buy</th><th className="right">Quantity</th><th className="right">Amount</th><th className="right">Part</th><th>State</th></tr>
          </thead>
          <tbody>
            {rec.steps.map((s) => (
              <tr key={s.step} className={s === next ? 'row-next' : undefined}>
                <td className="strong">{s.step}{s.step === 1 ? ' · minimum start' : ''}</td>
                <td>{s.levelPct}% below, at {price(s.levelPrice)}</td>
                <td>{s.instrument === 'cash' ? 'Shares' : 'Futures'}</td>
                <td className="right num">{s.quantity}</td>
                <td className="right num">{rupees(s.amount)}</td>
                <td className="right num">{s.step}</td>
                <td>{s.filled ? 'Bought' : s.reached ? 'Ready' : 'Not reached'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">{rec.futuresNote} Sell everything at {price(rec.targetPrice)}; close at {price(rec.hardExitPrice)}.</p>
      {rec.status === 'new' && next && (
        <div className="idea-actions">
          <fieldset className="mode-choice">
            <legend>Place this as</legend>
            <label><input type="radio" name={`mode-${rec.id}`} checked={mode === 'paper'} onChange={() => setMode('paper')} /> Paper trade</label>
            <label><input type="radio" name={`mode-${rec.id}`} checked={mode === 'real'} onChange={() => setMode('real')} /> Real trade</label>
          </fieldset>
          {mode === 'real' && <p className="note" role="status">Real trading is locked until the paper period is complete. Choose paper to continue.</p>}
          <div className="actions">
            <button type="button" className="button primary" disabled={busy || mode === 'real'} onClick={() => act(() => api.approve(rec.id, mode))}>
              {busy ? 'Working…' : `Approve step ${next.step}`}
            </button>
            <button type="button" className="button" disabled={busy} onClick={() => act(() => api.skip(rec.id, ''))}>Skip</button>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
        </div>
      )}
    </article>
  )
}

export function Ideas() {
  const [type, setType] = useState<InstrumentType | 'any'>('any')
  const [status, setStatus] = useState<RecStatus | 'any'>('any')
  const [minScore, setMinScore] = useState(0)
  const [minZone, setMinZone] = useState(0)
  const { data, error, loading, reload } = useAsync(
    () => api.listRecommendations({ instrumentType: type, status, minScore, minZone }),
    [type, status, minScore, minZone],
  )
  return (
    <>
      <header className="page-head">
        <div>
          <h1>Ideas</h1>
          <p className="muted">Approved stocks that are in a buy zone right now, with a plan for each.</p>
        </div>
      </header>
      <Card>
        <div className="filters">
          <label>Buy with
            <select value={type} onChange={(e) => setType(e.target.value as InstrumentType | 'any')}>
              <option value="any">Anything</option><option value="cash">Shares</option><option value="future">Futures</option><option value="combo">Shares and futures</option>
            </select>
          </label>
          <label>State
            <select value={status} onChange={(e) => setStatus(e.target.value as RecStatus | 'any')}>
              <option value="any">All</option><option value="new">Waiting for you</option><option value="approved">Approved</option><option value="skipped">Skipped</option>
            </select>
          </label>
          <label>Deepest zone at least
            <select value={minZone} onChange={(e) => setMinZone(Number(e.target.value))}>
              <option value={0}>Any</option><option value={1}>Zone 1</option><option value={2}>Zone 2</option><option value={3}>Zone 3</option>
            </select>
          </label>
          <label>Evidence score at least
            <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
              <option value={0}>Any</option><option value={60}>60</option><option value={70}>70</option><option value={80}>80</option>
            </select>
          </label>
        </div>
      </Card>
      <State loading={loading} error={error} empty={!data?.length && 'No ideas match. Ideas appear when an approved stock falls 10% or more below its 6-month high.'}>
        {data?.map((rec) => <IdeaCard key={rec.id} rec={rec} onChanged={reload} />)}
      </State>
      <p className="muted small">Ideas come from fixed rules, not advice. Nothing is bought without your approval.</p>
    </>
  )
}
