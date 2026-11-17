import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const LINKS = [
  { to: '/stocks', label: 'Stocks' },
  { to: '/ideas', label: 'Ideas' },
  { to: '/trades', label: 'Trades' },
  { to: '/runs', label: 'Algo runs' },
  { to: '/settings', label: 'Settings' },
]

export function Logo() {
  return (
    <span className="logo">
      <svg aria-hidden="true" width="24" height="24" viewBox="0 0 28 28" fill="none">
        <rect x="1" y="1" width="26" height="26" rx="7" fill="#1D4F5C" />
        <path d="M7 18l4.5-5 3.5 3 6-7" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Steady
    </span>
  )
}

export function Layout() {
  const { session, signOut } = useAuth()
  return (
    <div className="shell">
      <nav className="side" aria-label="Main">
        <Logo />
        <div className="side-links">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} className={({ isActive }) => (isActive ? 'side-link on' : 'side-link')}>
              {link.label}
            </NavLink>
          ))}
        </div>
        <div className="side-foot">
          <span className="muted small">{session?.email}</span>
          <button type="button" className="link-button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </nav>
      <main className="main">
        <div className="banner" role="note">
          Sample data: prices are a snapshot from 17 Nov 2026 and trades are paper only. Nothing here is sent to a broker.
        </div>
        <Outlet />
      </main>
    </div>
  )
}
