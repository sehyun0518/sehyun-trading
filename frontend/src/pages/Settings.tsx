import { useState, useEffect } from 'react'
import { api } from '../api/client'

function CheckIcon({ done }: { done: boolean }) {
  return (
    <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
      done ? 'bg-green-900 text-green-300' : 'bg-gray-800 text-gray-500'
    }`}>
      {done ? '✓' : '·'}
    </span>
  )
}

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

  const hasAnyCreds = Boolean(info?.has_paper_creds || info?.has_real_creds)
  const onboarding = [
    {
      title: '계정 생성',
      description: info?.email ?? '로그인된 계정을 확인합니다.',
      done: Boolean(info?.email),
    },
    {
      title: 'KIS 모의투자 자격증명 등록',
      description: info?.has_paper_creds
        ? `등록됨 (${info.kis_paper_account})`
        : '처음에는 모의투자 App Key, Secret, 계좌번호를 먼저 입력하세요.',
      done: Boolean(info?.has_paper_creds),
    },
    {
      title: '대시보드에서 후보/보유 종목 확인',
      description: hasAnyCreds
        ? '대시보드에서 후보 조회 시 전략 검증용 지표 스냅샷이 자동 저장됩니다.'
        : '자격증명을 등록하면 포트폴리오와 후보 종목을 확인할 수 있습니다.',
      done: hasAnyCreds,
    },
    {
      title: '실전투자는 별도 등록 후 전환',
      description: info?.has_real_creds
        ? `등록됨 (${info.kis_real_account})`
        : '실전 계정은 모의투자 흐름을 확인한 뒤 별도로 입력하세요.',
      done: Boolean(info?.has_real_creds),
    },
  ]

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
    <div className="max-w-5xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">설정</h2>
        <p className="mt-1 text-sm text-gray-500">가입 후 필요한 연결 상태와 KIS 자격증명을 관리합니다.</p>
      </div>

      {info && (
        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <section className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <h3 className="text-sm font-semibold text-gray-200">온보딩 체크리스트</h3>
            <div className="mt-4 space-y-4">
              {onboarding.map(item => (
                <div key={item.title} className="flex gap-3">
                  <CheckIcon done={item.done} />
                  <div>
                    <div className={item.done ? 'text-sm font-medium text-gray-100' : 'text-sm font-medium text-gray-300'}>
                      {item.title}
                    </div>
                    <div className="mt-1 text-xs leading-5 text-gray-500">{item.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm space-y-1">
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
            <div className="pt-3 text-xs leading-5 text-gray-500">
              후보 종목 조회 시점의 RSI, MA20, 거래량비, 외국인 순매수, 진입가/손절가/목표가가 자동 저장됩니다.
            </div>
          </section>
        </div>
      )}

      <form onSubmit={handleSave} className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3 rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h3 className="text-sm font-medium text-gray-300">KIS 모의투자</h3>
          {field('App Key', 'kis_paper_app_key')}
          {field('App Secret', 'kis_paper_app_secret')}
          {field('계좌번호', 'kis_paper_account', '12345678-01')}
        </div>

        <div className="space-y-3 rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h3 className="text-sm font-medium text-gray-300">KIS 실전투자</h3>
          {field('App Key', 'kis_real_app_key')}
          {field('App Secret', 'kis_real_app_secret')}
          {field('계좌번호', 'kis_real_account', '87654321-01')}
        </div>

        <div className="lg:col-span-2 flex items-center gap-4">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
          >
            {saving ? '저장 중...' : '저장'}
          </button>
          {message && (
            <p className={`text-sm ${message.includes('실패') ? 'text-red-400' : 'text-green-400'}`}>
              {message}
            </p>
          )}
        </div>
      </form>
    </div>
  )
}
