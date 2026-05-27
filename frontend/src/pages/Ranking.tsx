import useSWR from 'swr'
import { useState } from 'react'
import { api, RankType, RankItem } from '../api/client'

const TABS: { key: RankType; label: string; metric: string; format: (v: RankItem) => string }[] = [
  {
    key: 'volume',
    label: '거래량',
    metric: '거래량',
    format: (v) => `${(v.volume / 10000).toFixed(0)}만주`,
  },
  {
    key: 'trading_value',
    label: '거래대금',
    metric: '거래대금',
    format: (v) => `${(v.trading_value / 100_000_000).toFixed(0)}억`,
  },
  {
    key: 'change_rate',
    label: '상승률',
    metric: '등락률',
    format: (v) => `${v.change_pct > 0 ? '+' : ''}${v.change_pct.toFixed(2)}%`,
  },
  {
    key: 'market_cap',
    label: '시가총액',
    metric: '시가총액',
    format: (v) => v.market_cap != null ? `${(v.market_cap / 100_000_000).toFixed(0)}억` : '—',
  },
]

function fmt(n: number) { return n.toLocaleString('ko-KR') }

export default function Ranking() {
  const [tab, setTab] = useState<RankType>('volume')
  const currentTab = TABS.find(t => t.key === tab)!

  const { data, isLoading, error } = useSWR(
    ['ranking', tab],
    () => api.marketRanking(tab),
    { refreshInterval: 60_000 },
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200">시장 랭킹</h2>
        <span className="text-xs text-gray-500">1분마다 자동 갱신</span>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 rounded-lg border border-gray-800 bg-gray-900 p-1 w-fit">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              tab === t.key
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 본문 */}
      {isLoading && <div className="text-gray-500 text-sm">불러오는 중...</div>}
      {error && (
        <div className="rounded-lg border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-400">
          {error instanceof Error ? error.message : '데이터 조회 오류'}
        </div>
      )}
      {data && !data.items.length && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-8 text-center text-sm text-gray-600">
          데이터가 없습니다. 장 시간(09:00~15:30) 중 조회해주세요.
        </div>
      )}
      {data && data.items.length > 0 && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-gray-800">
                <th className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500 w-12">순위</th>
                <th className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500">종목</th>
                <th className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500 text-right">현재가</th>
                <th className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500 text-right">등락률</th>
                <th className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500 text-right">{currentTab.metric}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {data.items.map(item => (
                <tr key={item.ticker} className="hover:bg-gray-950 transition-colors">
                  <td className="py-2.5 px-4 text-gray-600 font-mono text-xs">{item.rank}</td>
                  <td className="py-2.5 px-4">
                    <div className="font-medium text-gray-100">{item.name || item.ticker}</div>
                    <div className="text-xs text-gray-500 font-mono">{item.ticker}</div>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono text-gray-300">{fmt(item.current_price)}</td>
                  <td className={`py-2.5 px-4 text-right font-mono font-semibold ${
                    item.change_pct > 0 ? 'text-red-400' : item.change_pct < 0 ? 'text-blue-400' : 'text-gray-400'
                  }`}>
                    {item.change_pct > 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                  </td>
                  <td className="py-2.5 px-4 text-right text-gray-300 font-mono">
                    {currentTab.format(item)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
