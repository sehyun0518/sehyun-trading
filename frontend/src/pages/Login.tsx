import { useState } from 'react'

const BASE = import.meta.env.VITE_API_URL ?? ''

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/api/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) {
        setError('패스워드가 올바르지 않습니다.')
        return
      }
      const { access_token } = await res.json()
      localStorage.setItem('auth_token', access_token)
      window.location.href = '/'
    } catch {
      setError('서버에 연결할 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-lg p-8 w-full max-w-sm space-y-4">
        <h1 className="text-lg font-bold text-blue-400">KR Swing Advisor</h1>
        <div>
          <label className="block text-sm text-gray-400 mb-1">패스워드</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            autoFocus
          />
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading || !password}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
        >
          {loading ? '로그인 중...' : '로그인'}
        </button>
      </form>
    </div>
  )
}
