import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Settings() {
  const [info, setInfo] = useState<{
    email: string
    has_paper_creds: boolean
    has_real_creds: boolean
    kis_paper_account: string | null
    kis_real_account: string | null
  } | null>(null)

  const [form, setForm] = useState({
    kis_paper_app_key: '', kis_paper_app_secret: '', kis_paper_account: '',
    kis_real_app_key: '',  kis_real_app_secret: '',  kis_real_account: '',
  })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.me().then(setInfo).catch(() => {})
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await api.updateSettings(form)
      setMessage('설정이 저장되었습니다.')
      const updated = await api.me()
      setInfo(updated)
    } catch {
      setMessage('저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  function field(label: string, key: keyof typeof form, placeholder = '') {
    return (
      <div>
        <label className="block text-sm text-gray-400 mb-1">{label}</label>
        <input
          type="password"
          value={form[key]}
          onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
          placeholder={placeholder || '변경 시에만 입력'}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 placeholder-gray-600"
        />
      </div>
    )
  }

  return (
    <div className="max-w-lg space-y-6">
      <h2 className="text-lg font-semibold text-white">설정</h2>

      {info && (
        <div className="bg-gray-900 border border-gray-800 rounded p-4 text-sm space-y-1">
          <p className="text-gray-400">이메일: <span className="text-white">{info.email}</span></p>
          <p className="text-gray-400">
            모의투자 자격증명:{' '}
            <span className={info.has_paper_creds ? 'text-green-400' : 'text-yellow-400'}>
              {info.has_paper_creds ? `등록됨 (${info.kis_paper_account})` : '미등록'}
            </span>
          </p>
          <p className="text-gray-400">
            실전투자 자격증명:{' '}
            <span className={info.has_real_creds ? 'text-green-400' : 'text-yellow-400'}>
              {info.has_real_creds ? `등록됨 (${info.kis_real_account})` : '미등록'}
            </span>
          </p>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-5">
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-300">KIS 모의투자</h3>
          {field('App Key', 'kis_paper_app_key')}
          {field('App Secret', 'kis_paper_app_secret')}
          {field('계좌번호', 'kis_paper_account', '12345678-01')}
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-300">KIS 실전투자</h3>
          {field('App Key', 'kis_real_app_key')}
          {field('App Secret', 'kis_real_app_secret')}
          {field('계좌번호', 'kis_real_account', '87654321-01')}
        </div>

        {message && (
          <p className={`text-sm ${message.includes('실패') ? 'text-red-400' : 'text-green-400'}`}>
            {message}
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
        >
          {saving ? '저장 중...' : '저장'}
        </button>
      </form>
    </div>
  )
}
