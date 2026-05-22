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
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-lg p-8 w-full max-w-sm space-y-4">
        <h1 className="text-lg font-bold text-blue-400">회원가입</h1>
        <div>
          <label className="block text-sm text-gray-400 mb-1">이메일</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            autoFocus
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">패스워드 (8자 이상)</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading || !email || !password}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
        >
          {loading ? '등록 중...' : '회원가입'}
        </button>
        <p className="text-center text-sm text-gray-500">
          이미 계정이 있으신가요?{' '}
          <a href="/login" className="text-blue-400 hover:underline">로그인</a>
        </p>
      </form>
    </div>
  )
}
