import { ALWAYS_ON_SERVER, ALWAYS_ON_TEXT } from '../constants'
import { Card } from './ui'

interface Props {
  /** True when the schedule runs on the server, where it cannot be paused from here yet. */
  server: boolean
  on: boolean
  onToggle: () => void
}

export function AlwaysOnCard({ server, on, onToggle }: Props) {
  if (server)
    return (
      <Card title="Always on">
        <p>{ALWAYS_ON_TEXT}</p>
        <p className="gain strong">{ALWAYS_ON_SERVER}</p>
      </Card>
    )
  return (
    <Card title="Always on" aside={
      <button type="button" role="switch" aria-checked={on} aria-label="Always on" className={on ? 'switch on' : 'switch'} onClick={onToggle}><span /></button>
    }>
      <p>{ALWAYS_ON_TEXT}</p>
      <p className={on ? 'gain strong' : 'muted'}>{on ? 'Running' : 'Paused. Runs only when you press Run now.'}</p>
    </Card>
  )
}
