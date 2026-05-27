import { useState } from 'react'

const BASE = import.meta.env.VITE_API_URL ?? ''

export default function Signup() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('패스워드는 8자 이상이어야 합니다.')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || '회원가입에 실패했습니다.')
        return
      }
      localStorage.setItem('auth_token', data.access_token)
      window.location.href = '/settings'
    } catch {
      setError('서버에 연결할 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <a href="/" className="text-lg font-bold text-blue-400">KR Swing Advisor</a>
          <p className="mt-1 text-sm text-gray-500">모의투자로 먼저 시작하세요</p>
        </div>
        <form onSubmit={handleSubmit} className="rounded-lg border border-gray-800 bg-gray-900 p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">이메일</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none transition-colors"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">패스워드 <span className="normal-case font-normal">(8자 이상)</span></label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none transition-colors"
            />
          </div>
          {error && (
            <div className="rounded border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? '등록 중...' : '계정 만들기'}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500">
          이미 계정이 있으신가요?{' '}
          <a href="/login" className="text-blue-400 hover:text-blue-300 transition-colors">로그인</a>
        </p>
      </div>
    </div>
  )
}
