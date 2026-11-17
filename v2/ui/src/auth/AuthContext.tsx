import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api } from '../api'
import type { Session } from '../api/types'
import { ROUTES, SESSION_KEY } from '../constants'
import { readJson, remove, writeJson } from '../lib/storage'

interface AuthValue {
  session: Session | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => readJson<Session>(SESSION_KEY))
  const value = useMemo<AuthValue>(
    () => ({
      session,
      async signIn(email, password) {
        const next = await api.signIn(email, password)
        writeJson(SESSION_KEY, next)
        setSession(next)
      },
      signOut() {
        remove(SESSION_KEY)
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
  if (!session) return <Navigate to={ROUTES.signIn} replace state={{ from: location.pathname }} />
  return <>{children}</>
}
