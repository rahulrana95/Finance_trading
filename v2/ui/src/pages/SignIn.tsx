import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Logo } from '../components/Layout'
import { DEMO_EMAIL, DEMO_PASSWORD } from '../api/mock/data'
import { USING_MOCK } from '../api'

export function SignIn() {
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({})
  const [busy, setBusy] = useState(false)
  const from = (location.state as { from?: string } | null)?.from ?? '/stocks'

  if (session) return <Navigate to={from} replace />

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next: typeof errors = {}
    if (!email.trim()) next.email = 'Enter your email.'
    else if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'That does not look like an email address.'
    if (!password) next.password = 'Enter your password.'
    setErrors(next)
    if (next.email || next.password) return
    setBusy(true)
    try {
      await signIn(email, password)
      navigate(from, { replace: true })
    } catch (e) {
      setPassword('')
      setErrors({ form: e instanceof Error ? e.message : 'Could not sign in.' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="signin">
      <Logo />
      <form className="card signin-card" onSubmit={submit} noValidate>
        <div>
          <h1>Sign in</h1>
          <p className="muted">Your positions and rules are private to this account.</p>
        </div>
        {errors.form && <p className="error" role="alert">{errors.form}</p>}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!errors.email} aria-describedby={errors.email ? 'email-error' : undefined} />
          {errors.email && <span id="email-error" className="field-error">{errors.email}</span>}
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} aria-describedby={errors.password ? 'password-error' : undefined} />
          {errors.password && <span id="password-error" className="field-error">{errors.password}</span>}
        </div>
        <button type="submit" className="button primary" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        {USING_MOCK && (
          <p className="hint">
            Demo build with sample data. Use <strong>{DEMO_EMAIL}</strong> and password <strong>{DEMO_PASSWORD}</strong>.
          </p>
        )}
      </form>
      <p className="muted small center">Signing in never places an order. The app trades on paper only.</p>
    </div>
  )
}
