import type { StockStatus } from '../api/types'
import { STOCK_STATUS_KIND, STOCK_STATUS_LABEL } from '../constants'
import { Card, Pill } from './ui'

const CHOICES: Array<{ status: StockStatus; label: string; primary?: boolean }> = [
  { status: 'approved', label: 'Approve', primary: true },
  { status: 'watching', label: 'Keep watching' },
  { status: 'rejected', label: 'Reject' },
]

interface Props {
  status: StockStatus
  /** True while the server cannot save a decision yet (it needs sign-in first). */
  readOnly: boolean
  onChange: (status: StockStatus) => void
}

export function DecisionCard({ status, readOnly, onChange }: Props) {
  return (
    <Card title="Your decision" aside={<Pill kind={STOCK_STATUS_KIND[status]}>{STOCK_STATUS_LABEL[status]}</Pill>}>
      <p className="muted">Only approved stocks get buy ideas.</p>
      {readOnly ? (
        <p className="note">Changing a stock's status from here arrives with sign-in on the server.</p>
      ) : (
        <div className="actions">
          {CHOICES.map((c) => (
            <button key={c.status} type="button" className={c.primary ? 'button primary' : 'button'} disabled={status === c.status} onClick={() => onChange(c.status)}>
              {c.label}
            </button>
          ))}
        </div>
      )}
    </Card>
  )
}
