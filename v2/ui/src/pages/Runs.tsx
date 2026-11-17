import { useState } from 'react'
import { api } from '../api'
import type { RunKind } from '../api/types'
import { Card, State } from '../components/ui'
import { dateTime } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const KIND: Record<RunKind, string> = { scheduled: 'Scheduled', on_demand: 'On demand', dry_run: 'Dry run', screener: 'Screener' }

export function Runs() {
  const runs = useAsync(() => api.listRuns(), [])
  const settings = useAsync(() => api.getSettings(), [])
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<string>()
  const current = runs.data?.find((r) => r.id === selected) ?? runs.data?.[0]

  async function start(kind: RunKind) {
    setBusy(true)
    try {
      const run = await api.startRun(kind)
      setSelected(run.id)
      runs.reload()
    } finally {
      setBusy(false)
    }
  }
  async function toggleAlwaysOn() {
    await api.updateSettings({ alwaysOn: !settings.data?.alwaysOn })
    settings.reload()
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Algo runs</h1>
          <p className="muted">Every check the app makes, in plain words.</p>
        </div>
      </header>
      <div className="grid two">
        <Card title="Always on" aside={
          <button type="button" role="switch" aria-checked={settings.data?.alwaysOn ?? false} aria-label="Always on" className={settings.data?.alwaysOn ? 'switch on' : 'switch'} onClick={toggleAlwaysOn}><span /></button>
        }>
          <p>Checks every 5 minutes while the market is open, and updates data at 18:30 every day.</p>
          <p className={settings.data?.alwaysOn ? 'gain strong' : 'muted'}>{settings.data?.alwaysOn ? 'Running' : 'Paused. Runs only when you press Run now.'}</p>
        </Card>
        <Card title="Run on demand">
          <p>Run one check now with the same rules. A dry run shows the reasoning without creating ideas.</p>
          <div className="actions">
            <button type="button" className="button primary" disabled={busy} onClick={() => start('on_demand')}>Run now</button>
            <button type="button" className="button" disabled={busy} onClick={() => start('dry_run')}>Dry run</button>
          </div>
        </Card>
      </div>
      <div className="grid runs">
        <Card title={current ? `${KIND[current.kind]} run · ${dateTime(current.startedAt)}` : 'Latest run'} aside={current && <span className="muted">{current.summary}</span>}>
          <State loading={runs.loading} error={runs.error} empty={!current && 'No runs yet.'}>
            <ol className="steps" aria-label="Run steps">
              {current?.steps.map((s) => (
                <li key={s.seq} className={`step step-${s.level}`}>
                  <span className="step-subject">{s.subject}</span>
                  <span>{s.message}</span>
                </li>
              ))}
            </ol>
          </State>
        </Card>
        <Card title="Earlier runs">
          <ul className="run-list">
            {runs.data?.map((r) => (
              <li key={r.id}>
                <button type="button" className={r.id === current?.id ? 'run-item on' : 'run-item'} onClick={() => setSelected(r.id)}>
                  <span>{dateTime(r.startedAt)} · {KIND[r.kind]}</span>
                  <span className="muted">{r.summary}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
