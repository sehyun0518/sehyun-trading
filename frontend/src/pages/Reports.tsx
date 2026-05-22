import useSWR from 'swr'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { api, ReportMeta, ReportDetail } from '../api/client'

type Tab = 'analysis' | 'candidates' | 'warnings'

function TickerBadge({ ticker }: { ticker: string }) {
  return (
    <span className="inline-block px-2 py-0.5 rounded bg-gray-800 text-blue-300 text-xs font-mono border border-gray-700">
      {ticker}
    </span>
  )
}

function ReportContent({ date }: { date: string }) {
  const { data: detail, isLoading } = useSWR<ReportDetail>(
    `report-${date}`, () => api.reportDetail(date)
  )
  const [tab, setTab] = useState<Tab>('analysis')

  const candidates = (detail?.candidates ?? []) as string[]
  const warnings = (detail?.warnings ?? []) as string[]

  if (isLoading) return <div className="text-gray-500 text-sm p-6">불러오는 중...</div>
  if (!detail) return <div className="text-gray-600 text-sm p-6">리포트 없음</div>

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'analysis', label: 'AI 분석' },
    { id: 'candidates', label: '후보 종목', count: candidates.length },
    { id: 'warnings', label: '경고', count: warnings.length },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* 헤더 */}
      <div className="px-6 pt-5 pb-0 border-b border-gray-800">
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-base font-semibold text-gray-100">{detail.date} 주간 리포트</h2>
          {candidates.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900 text-blue-300">
              후보 {candidates.length}종목
            </span>
          )}
          {warnings.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-900 text-yellow-300">
              경고 {warnings.length}건
            </span>
          )}
        </div>
        {/* 탭 */}
        <div className="flex gap-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
                tab === t.id
                  ? 'bg-gray-950 text-white border-t border-x border-gray-700'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className="ml-1.5 text-xs opacity-70">{t.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 탭 콘텐츠 */}
      <div className="flex-1 overflow-y-auto p-6">

        {tab === 'analysis' && (
          detail.content ? (
            <div className="prose prose-invert prose-sm max-w-none
              prose-headings:text-gray-100 prose-headings:font-semibold
              prose-h1:text-lg prose-h2:text-base prose-h2:border-b prose-h2:border-gray-800 prose-h2:pb-2
              prose-h3:text-sm prose-h3:text-gray-300
              prose-p:text-gray-300 prose-p:leading-relaxed
              prose-li:text-gray-300
              prose-strong:text-gray-100
              prose-table:text-sm prose-th:text-gray-400 prose-th:font-medium prose-td:text-gray-300
              prose-td:border-gray-800 prose-th:border-gray-700
              prose-a:text-blue-400 prose-code:text-yellow-300 prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded
              prose-hr:border-gray-700 prose-blockquote:border-gray-600 prose-blockquote:text-gray-400">
              <ReactMarkdown>{detail.content}</ReactMarkdown>
            </div>
          ) : (
            <div className="text-gray-600 text-sm">AI 분석 내용 없음</div>
          )
        )}

        {tab === 'candidates' && (
          candidates.length === 0 ? (
            <div className="text-gray-600 text-sm">후보 종목 없음</div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-gray-500">해당 주 규칙을 통과한 진입 후보 종목입니다.</p>
              <div className="flex flex-wrap gap-2">
                {candidates.map((ticker: string) => (
                  <TickerBadge key={ticker} ticker={ticker} />
                ))}
              </div>
            </div>
          )
        )}

        {tab === 'warnings' && (
          warnings.length === 0 ? (
            <div className="text-gray-600 text-sm">경고 없음</div>
          ) : (
            <div className="space-y-2">
              {warnings.map((w, i) => (
                <div key={i} className="flex gap-3 bg-yellow-950 border border-yellow-900 rounded-lg px-4 py-3 text-sm text-yellow-200">
                  <span className="text-yellow-500 mt-0.5">⚠</span>
                  <span>{String(w)}</span>
                </div>
              ))}
            </div>
          )
        )}

      </div>
    </div>
  )
}

export default function Reports() {
  const { data: list = [], isLoading } = useSWR<ReportMeta[]>('reports', api.reports)
  const [selected, setSelected] = useState<string | null>(null)

  const activeDate = selected ?? list[0]?.date ?? null

  if (isLoading) return <div className="text-gray-500 text-sm">불러오는 중...</div>

  if (list.length === 0) {
    return (
      <div className="text-gray-600 text-sm">
        아직 생성된 리포트가 없습니다. 매주 월요일 07:00 자동 생성됩니다.
      </div>
    )
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">

      {/* 사이드바 */}
      <aside className="w-52 shrink-0 overflow-y-auto">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">리포트 히스토리</h2>
        <ul className="space-y-1">
          {list.map(r => (
            <li key={r.date}>
              <button
                onClick={() => setSelected(r.date)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  activeDate === r.date
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <div className="font-medium">{r.date}</div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`text-xs ${activeDate === r.date ? 'opacity-70' : 'text-gray-600'}`}>
                    후보 {r.candidates_count}종목
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* 리포트 본문 */}
      <div className="flex-1 overflow-hidden bg-gray-900 rounded-xl border border-gray-800">
        {activeDate
          ? <ReportContent date={activeDate} />
          : <div className="text-gray-600 text-sm p-6">리포트를 선택하세요</div>
        }
      </div>

    </div>
  )
}
