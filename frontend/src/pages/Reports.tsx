import useSWR from 'swr'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { api, ReportMeta, ReportDetail } from '../api/client'

type Tab = 'analysis' | 'candidates' | 'warnings'

function StatCard({ label, value, tone }: { label: string; value: string | number; tone?: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950 px-4 py-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${tone ?? 'text-gray-100'}`}>{value}</div>
    </div>
  )
}

function ReportContent({ date }: { date: string }) {
  const { data: detail, isLoading } = useSWR<ReportDetail>(
    `report-${date}`, () => api.reportDetail(date)
  )
  const [tab, setTab] = useState<Tab>('analysis')

  const candidates = (detail?.candidates ?? []) as string[]
  const warnings = (detail?.warnings ?? []) as string[]

  if (isLoading) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-gray-500 text-sm">불러오는 중...</div>
    </div>
  )
  if (!detail) return <div className="text-gray-600 text-sm p-6">리포트 없음</div>

  const tabs: { id: Tab; label: string; count?: number; badge?: string }[] = [
    { id: 'analysis', label: 'AI 분석' },
    { id: 'candidates', label: '후보 종목', count: candidates.length, badge: candidates.length > 0 ? 'blue' : undefined },
    { id: 'warnings', label: '경고', count: warnings.length, badge: warnings.length > 0 ? 'yellow' : undefined },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* 리포트 헤더 */}
      <div className="px-6 pt-5 border-b border-gray-800">
        <div className="mb-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">주간 리포트</div>
          <div className="text-base font-semibold text-gray-100">{detail.date}</div>
        </div>

        {/* 지표 요약 */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <StatCard label="진입 후보" value={`${candidates.length}종목`} tone={candidates.length > 0 ? 'text-blue-300' : 'text-gray-500'} />
          <StatCard label="경고 종목" value={`${warnings.length}건`} tone={warnings.length > 0 ? 'text-yellow-300' : 'text-gray-500'} />
          <StatCard label="기준일" value={detail.date} tone="text-gray-300" />
        </div>

        {/* 탭 */}
        <div className="flex gap-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t transition-colors ${
                tab === t.id
                  ? 'bg-gray-950 text-white border-t border-x border-gray-700'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className={`inline-flex items-center justify-center h-4 min-w-4 px-1 rounded-full text-xs font-bold ${
                  t.badge === 'blue' ? 'bg-blue-950 text-blue-300' :
                  t.badge === 'yellow' ? 'bg-yellow-950 text-yellow-300' :
                  'bg-gray-800 text-gray-400'
                }`}>{t.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 탭 콘텐츠 */}
      <div className="flex-1 overflow-y-auto p-6">

        {tab === 'analysis' && (
          detail.content ? (
            <div>
              {/* 분석 요약 배너 */}
              {(candidates.length > 0 || warnings.length > 0) && (
                <div className="mb-6 rounded-lg border border-gray-800 bg-gray-950 px-4 py-3 text-sm flex flex-wrap gap-4">
                  {candidates.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-blue-400 shrink-0" />
                      <span className="text-gray-400">진입 후보 <span className="font-semibold text-blue-300">{candidates.length}종목</span> 검토됨</span>
                    </div>
                  )}
                  {warnings.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-yellow-400 shrink-0" />
                      <span className="text-gray-400">보유 종목 <span className="font-semibold text-yellow-300">{warnings.length}건</span> 점검 필요</span>
                    </div>
                  )}
                </div>
              )}

              <div className="prose prose-invert prose-sm max-w-none
                [&_h1]:text-base [&_h1]:font-semibold [&_h1]:text-gray-100 [&_h1]:mt-6 [&_h1]:mb-3 [&_h1]:pb-2 [&_h1]:border-b [&_h1]:border-gray-800
                [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:text-gray-200 [&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:pb-1.5 [&_h2]:border-b [&_h2]:border-gray-800
                [&_h3]:text-sm [&_h3]:font-medium [&_h3]:text-gray-300 [&_h3]:mt-4 [&_h3]:mb-1.5
                [&_p]:text-gray-300 [&_p]:leading-7 [&_p]:text-sm [&_p]:my-2
                [&_ul]:my-2 [&_ul]:space-y-1 [&_ol]:my-2 [&_ol]:space-y-1
                [&_li]:text-gray-300 [&_li]:text-sm [&_li]:leading-6
                [&_li]:before:text-blue-400
                [&_strong]:text-gray-100 [&_strong]:font-semibold
                [&_em]:text-gray-400
                [&_blockquote]:border-l-2 [&_blockquote]:border-blue-800 [&_blockquote]:pl-4 [&_blockquote]:text-gray-400 [&_blockquote]:italic [&_blockquote]:my-3
                [&_code]:text-yellow-300 [&_code]:bg-gray-800 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_code]:font-mono
                [&_pre]:bg-gray-800 [&_pre]:rounded-lg [&_pre]:p-4 [&_pre]:overflow-x-auto [&_pre]:my-3
                [&_hr]:border-gray-800 [&_hr]:my-4
                [&_table]:text-sm [&_table]:w-full [&_table]:my-3
                [&_thead]:border-b [&_thead]:border-gray-700
                [&_th]:text-left [&_th]:py-2 [&_th]:pr-4 [&_th]:text-xs [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-wider [&_th]:text-gray-500
                [&_td]:py-2 [&_td]:pr-4 [&_td]:text-gray-300 [&_td]:border-b [&_td]:border-gray-800
                [&_a]:text-blue-400 [&_a]:underline
              ">
                <ReactMarkdown>{detail.content}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="text-2xl mb-3">📄</div>
              <div className="text-sm text-gray-500">AI 분석 내용이 없습니다.</div>
            </div>
          )
        )}

        {tab === 'candidates' && (
          candidates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="text-2xl mb-3">🔍</div>
              <div className="text-sm text-gray-500">이번 주 규칙을 통과한 후보 종목이 없습니다.</div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border border-blue-900 bg-blue-950/30 px-4 py-3 text-sm text-blue-300">
                규칙 엔진이 이번 주 선별한 진입 후보입니다. 개별 종목은 AI 분석 탭에서 확인하세요.
              </div>
              <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-hidden">
                {candidates.map((ticker: string, i: number) => (
                  <div key={ticker} className="flex items-center gap-4 px-4 py-3 border-b border-gray-800 last:border-b-0 hover:bg-gray-950 transition-colors">
                    <span className="text-xs font-bold text-gray-600 w-5 text-right shrink-0">{i + 1}</span>
                    <span className="font-mono text-sm font-semibold text-blue-300">{ticker}</span>
                  </div>
                ))}
              </div>
            </div>
          )
        )}

        {tab === 'warnings' && (
          warnings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="text-2xl mb-3">✓</div>
              <div className="text-sm text-gray-500">이번 주 경고 종목이 없습니다. 보유 종목 모두 정상 범위입니다.</div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border border-yellow-900 bg-yellow-950/30 px-4 py-3 text-sm text-yellow-300">
                청산 조건 충족·근접 종목입니다. 각 항목을 확인하고 보유 유지 여부를 직접 판단하세요.
              </div>
              {warnings.map((w, i) => (
                <div key={i} className="rounded-lg border border-yellow-900 bg-gray-900 px-4 py-4">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-yellow-950 text-yellow-400 text-xs font-bold border border-yellow-900">
                      !
                    </span>
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wider text-yellow-500 mb-1">경고 {i + 1}</div>
                      <p className="text-sm text-gray-200 leading-6">{String(w)}</p>
                    </div>
                  </div>
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
      <div className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-12 text-center">
        <div className="text-2xl mb-3">📋</div>
        <div className="text-sm text-gray-500">아직 생성된 리포트가 없습니다.</div>
        <div className="text-xs text-gray-600 mt-1">매주 월요일 07:00 자동 생성됩니다.</div>
      </div>
    )
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">

      {/* 사이드바 */}
      <aside className="w-52 shrink-0 overflow-y-auto">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">리포트 히스토리</h2>
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
                <div className="mt-0.5 flex items-center gap-1.5">
                  <span className={`text-xs ${activeDate === r.date ? 'text-blue-200' : 'text-gray-600'}`}>
                    후보 {r.candidates_count}종목
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* 리포트 본문 */}
      <div className="flex-1 overflow-hidden rounded-xl border border-gray-800 bg-gray-900">
        {activeDate
          ? <ReportContent date={activeDate} />
          : <div className="text-gray-600 text-sm p-6">리포트를 선택하세요</div>
        }
      </div>

    </div>
  )
}
