import { api } from '../api'
import { fetchHealth } from '../api/health'
import { Card, Pill, State } from '../components/ui'
import { BROKERS } from '../constants'
import { rupees } from '../lib/format'
import { useAsync } from '../lib/useAsync'


export function Settings() {
  const { data: s, error, loading, reload } = useAsync(() => api.getSettings(), [])
  const health = useAsync(fetchHealth, [])
  async function toggleKill() {
    await api.updateSettings({ killSwitch: !s?.killSwitch })
    reload()
  }
  return (
    <>
      <header className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="muted">How the app trades, and through which broker.</p>
        </div>
      </header>
      <State loading={loading} error={error}>
        {s && (
          <>
            <Card title="Trading mode">
              <div className="choice-grid">
                <div className="choice on"><span className="strong">Paper trading</span><span>Uses market prices and pretend money. No order reaches a broker.</span><Pill kind="good">In use</Pill></div>
                <div className="choice"><span className="strong">Real trading</span><span>Sends real orders through your broker.</span><Pill kind="neutral">Locked</Pill></div>
              </div>
              <p className="note">Real trading unlocks after 8 weeks of paper results and your decision. 0 of 8 weeks done.</p>
            </Card>
            <Card title="New orders" aside={<Pill kind={s.killSwitch ? 'bad' : 'good'}>{s.killSwitch ? 'Stopped' : 'Allowed'}</Pill>}>
              <p>Stopping blocks every new buy. Exits still work.</p>
              <button type="button" className={s.killSwitch ? 'button primary' : 'button danger'} onClick={toggleKill}>
                {s.killSwitch ? 'Allow new orders' : 'Stop all new orders'}
              </button>
            </Card>
            <Card title="Broker">
              <ul className="broker-list">
                {BROKERS.map((b) => (
                  <li key={b}><span className="strong">{b}</span><span className="muted">Not connected</span><button type="button" className="button" disabled>Connect</button></li>
                ))}
              </ul>
              <p className="muted small">Broker connections arrive with the backend. Until then prices come from a public snapshot.</p>
            </Card>
            <Card title="Backend" aside={<Pill kind={health.data ? 'good' : 'neutral'}>{health.loading ? 'Checking' : health.data ? 'Connected' : 'Not connected'}</Pill>}>
              <p>
                {health.data
                  ? `The server is running (version ${health.data.version.slice(0, 7)}). Screens still use sample data until each one is switched over.`
                  : 'No server is answering. Every screen is running on sample data in your browser.'}
              </p>
            </Card>
            <Card title="Limits">
              <dl className="rows">
                <div><dt>Paper capital</dt><dd className="num">{rupees(s.paperCapital)}</dd></div>
                <div><dt>Most money in one stock</dt><dd className="num">{s.perStockCapPct}% of capital</dd></div>
                <div><dt>Buy levels below the 6-month high</dt><dd className="num">{s.levels.join('%, ')}%</dd></div>
                <div><dt>Parts per step</dt><dd className="num">{s.parts.join(' : ')}</dd></div>
                <div><dt>Exit and stop</dt><dd className="num">{s.hardExitPct}% below</dd></div>
                <div><dt>Pause new buys when capital is down</dt><dd className="num">{s.pauseDrawdownPct}%</dd></div>
              </dl>
            </Card>
          </>
        )}
      </State>
    </>
  )
}
