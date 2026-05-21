import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Reports from './pages/Reports'

const nav = 'px-4 py-2 rounded text-sm font-medium transition-colors'
const active = 'bg-blue-600 text-white'
const inactive = 'text-gray-400 hover:text-white hover:bg-gray-800'

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <span className="font-bold text-blue-400 text-lg">KR Swing Advisor</span>
        <nav className="flex gap-2">
          <NavLink to="/" end className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
            대시보드
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>
            리포트
          </NavLink>
        </nav>
      </header>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
      </main>
    </div>
  )
}
