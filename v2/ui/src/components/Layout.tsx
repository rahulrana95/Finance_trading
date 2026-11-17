import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { LIVE } from '../api'
import { NAV_LINKS } from '../constants'
import { bannerText } from '../lib/format'

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
          {NAV_LINKS.map((link) => (
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
          {bannerText(LIVE)}
        </div>
        <Outlet />
      </main>
    </div>
  )
}
