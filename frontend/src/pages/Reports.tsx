import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { api, ReportMeta, ReportDetail } from '../api/client'

export default function Reports() {
  const [list, setList] = useState<ReportMeta[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [detail, setDetail] = useState<ReportDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    api.reports().then(r => {
      setList(r)
      if (r.length > 0) setSelected(r[0].date)
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selected) return
    setDetailLoading(true)
    api.reportDetail(selected)
      .then(setDetail)
      .finally(() => setDetailLoading(false))
  }, [selected])

  if (loading) return <div className="text-gray-500 text-sm">불러오는 중...</div>

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">

      {/* 리포트 목록 */}
      <aside className="w-52 shrink-0 overflow-y-auto">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">리포트 히스토리</h2>
        <ul className="space-y-1">
          {list.map(r => (
            <li key={r.date}>
              <button
                onClick={() => setSelected(r.date)}
                className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                  selected === r.date
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <div>{r.date}</div>
                <div className="text-xs opacity-70">후보 {r.candidates_count}종목</div>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* 리포트 본문 */}
      <div className="flex-1 overflow-y-auto bg-gray-900 rounded-lg p-6 border border-gray-800">
        {detailLoading ? (
          <div className="text-gray-500 text-sm">불러오는 중...</div>
        ) : detail?.content ? (
          <div className="prose prose-invert prose-sm max-w-none
            prose-headings:text-gray-100 prose-p:text-gray-300
            prose-table:text-gray-300 prose-th:text-gray-400
            prose-a:text-blue-400 prose-code:text-yellow-300
            prose-hr:border-gray-700">
            <ReactMarkdown>{detail.content}</ReactMarkdown>
          </div>
        ) : (
          <div className="text-gray-600 text-sm">리포트 내용 없음</div>
        )}
      </div>

    </div>
  )
}
