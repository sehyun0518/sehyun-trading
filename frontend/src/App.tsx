import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Reports from './pages/Reports'
import Orders from './pages/Orders'
import Ranking from './pages/Ranking'
import PublicHome from './pages/PublicHome'
import Legal from './pages/Legal'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Settings from './pages/Settings'
import { api } from './api/client'

const nav = 'px-3 py-1.5 rounded text-sm font-medium transition-colors'
const active = 'bg-blue-600 text-white'
const inactive = 'text-gray-400 hover:text-white hover:bg-gray-800'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('auth_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const [mode, setMode] = useState<'paper' | 'real'>('paper')
  const [switching, setSwitching] = useState(false)

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/health`)
      .then(r => r.json())
      .then(d => setMode(d.mode))
      .catch(() => {})
  }, [])

  async function toggleMode() {
    const next = mode === 'paper' ? 'real' : 'paper'
    setSwitching(true)
    try {
      await api.setMode(next)
      setMode(next)
    } finally {
      setSwitching(false)
    }
  }

  function logout() {
    localStorage.removeItem('auth_token')
    window.location.href = '/login'
  }

  return (
    <Routes>
      <Route path="/" element={<PublicHome />} />
      <Route path="/legal/:doc" element={<Legal />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/*" element={
        <RequireAuth>
          <div className="min-h-screen bg-gray-950 text-gray-100">
            <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-4">
              <span className="font-bold text-blue-400 text-base shrink-0">KR Swing Advisor</span>
              <nav className="flex gap-1 overflow-x-auto">
                <NavLink to="/" end className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
                  홈
                </NavLink>
                <NavLink to="/dashboard" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
                  대시보드
                </NavLink>
                <NavLink to="/reports" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
                  리포트
                </NavLink>
                <NavLink to="/orders" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
                  주문내역
                </NavLink>
                <NavLink to="/ranking" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
                  랭킹
                </NavLink>
                <NavLink to="/settings" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
                  설정
                </NavLink>
              </nav>
              <div className="ml-auto flex items-center gap-2 shrink-0">
                <span className={`text-xs px-2 py-1 rounded border font-semibold ${
                  mode === 'paper'
                    ? 'bg-yellow-950 border-yellow-900 text-yellow-300'
                    : 'bg-emerald-950 border-emerald-900 text-emerald-400'
                }`}>
                  {mode === 'paper' ? '모의투자' : '실전투자'}
                </span>
                <button
                  onClick={toggleMode}
                  disabled={switching}
                  className="text-xs px-3 py-1.5 rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors disabled:opacity-50"
                >
                  {switching ? '전환 중...' : mode === 'paper' ? '실전 전환' : '모의 전환'}
                </button>
                <button
                  onClick={logout}
                  className="text-xs px-3 py-1.5 rounded border border-gray-700 text-gray-400 hover:text-red-400 hover:border-red-800 transition-colors"
                >
                  로그아웃
                </button>
              </div>
            </header>
            <main className="p-6">
              <Routes>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/orders" element={<Orders />} />
                <Route path="/ranking" element={<Ranking />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </main>
          </div>
        </RequireAuth>
      } />
    </Routes>
  )
}
