import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api } from '../api'
import type { Session } from '../api/types'

const KEY = 'steady.session'

interface AuthValue {
  session: Session | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

function stored(): Session | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(stored)
  const value = useMemo<AuthValue>(
    () => ({
      session,
      async signIn(email, password) {
        const next = await api.signIn(email, password)
        try {
          sessionStorage.setItem(KEY, JSON.stringify(next))
        } catch {
          /* storage can be blocked; the session then lasts until reload */
        }
        setSession(next)
      },
      signOut() {
        try {
          sessionStorage.removeItem(KEY)
        } catch {
          /* nothing to clear */
        }
        setSession(null)
      },
    }),
    [session],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  const location = useLocation()
  if (!session) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />
  return <>{children}</>
}
