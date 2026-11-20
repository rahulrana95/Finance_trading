import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { Ideas } from './pages/Ideas'
import { Runs } from './pages/Runs'
import { Screener } from './pages/Screener'
import { Settings } from './pages/Settings'
import { SignIn } from './pages/SignIn'
import { StockDetail } from './pages/StockDetail'
import { Stocks } from './pages/Stocks'
import { Trades } from './pages/Trades'
import { ROUTES } from './constants'

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path={ROUTES.signIn} element={<SignIn />} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path={ROUTES.stocks} element={<Stocks />} />
          <Route path={`${ROUTES.stocks}/:symbol`} element={<StockDetail />} />
          <Route path={ROUTES.screener} element={<Screener />} />
          <Route path={ROUTES.ideas} element={<Ideas />} />
          <Route path={ROUTES.trades} element={<Trades />} />
          <Route path={ROUTES.runs} element={<Runs />} />
          <Route path={ROUTES.settings} element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to={ROUTES.stocks} replace />} />
      </Routes>
    </AuthProvider>
  )
}
