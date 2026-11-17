import type { ReactNode } from 'react'
import type { ModeFilter } from '../api/types'
import { signedRupees, tone } from '../lib/format'

export function Card({ title, aside, children }: { title?: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || aside) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  )
}

export function Pill({ kind, children }: { kind: 'neutral' | 'good' | 'warn' | 'bad' | 'accent'; children: ReactNode }) {
  return <span className={`pill pill-${kind}`}>{children}</span>
}

export function Meter({ value, label }: { value: number; label: string }) {
  return (
    <div className="meter" role="img" aria-label={`${label} ${value} out of 100`}>
      <div style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

export function Money({ value }: { value: number }) {
  return <span className={`num ${tone(value)}`}>{signedRupees(value)}</span>
}

export function State({ loading, error, empty, children }: { loading: boolean; error?: string; empty?: string | false; children: ReactNode }) {
  if (loading) return <p className="muted" role="status">Loading…</p>
  if (error) return <p className="error" role="alert">{error}</p>
  if (empty) return <p className="muted">{empty}</p>
  return <>{children}</>
}

const MODES: Array<{ value: ModeFilter; label: string }> = [
  { value: 'paper', label: 'Paper' },
  { value: 'real', label: 'Real' },
  { value: 'all', label: 'All' },
]

export function ModeTabs({ value, onChange }: { value: ModeFilter; onChange: (mode: ModeFilter) => void }) {
  return (
    <div className="tabs" role="group" aria-label="Show trades">
      {MODES.map((m) => (
        <button key={m.value} type="button" aria-pressed={value === m.value} className={value === m.value ? 'tab on' : 'tab'} onClick={() => onChange(m.value)}>
          {m.label}
        </button>
      ))}
    </div>
  )
}
