import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { Ideas } from './pages/Ideas'
import { Runs } from './pages/Runs'
import { Settings } from './pages/Settings'
import { SignIn } from './pages/SignIn'
import { StockDetail } from './pages/StockDetail'
import { Stocks } from './pages/Stocks'
import { Trades } from './pages/Trades'

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/sign-in" element={<SignIn />} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/stocks" element={<Stocks />} />
          <Route path="/stocks/:symbol" element={<StockDetail />} />
          <Route path="/ideas" element={<Ideas />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/stocks" replace />} />
      </Routes>
    </AuthProvider>
  )
}
