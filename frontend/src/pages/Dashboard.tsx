import { useEffect, useState } from 'react'
import { api, PortfolioResponse, CandidatesResponse } from '../api/client'

function fmt(n: number) { return n.toLocaleString('ko-KR') }
function pct(n: number) {
  const color = n > 0 ? 'text-red-400' : n < 0 ? 'text-blue-400' : 'text-gray-400'
  return <span className={color}>{n > 0 ? '+' : ''}{n.toFixed(2)}%</span>
}

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null)
  const [candidates, setCandidates] = useState<CandidatesResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.portfolio(), api.candidates()])
      .then(([p, c]) => { setPortfolio(p); setCandidates(c) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500 text-sm">불러오는 중...</div>

  const s = portfolio?.summary
  const mode = portfolio?.mode === 'paper' ? '모의투자' : '실전투자'

  return (
    <div className="space-y-8">

      {/* 포트폴리오 요약 */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-base font-semibold text-gray-200">포트폴리오 현황</h2>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">{mode}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '총평가금액', value: `${fmt(s?.total ?? 0)}원` },
            { label: '주식평가금액', value: `${fmt(s?.total_eval ?? 0)}원` },
            { label: '현금', value: `${fmt(s?.cash ?? 0)}원` },
            { label: '현금비중', value: `${s?.cash_ratio ?? 100}%` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <div className="text-xs text-gray-500 mb-1">{label}</div>
              <div className="text-lg font-semibold">{value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 보유 종목 */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-4">
          보유 종목 <span className="text-gray-500 font-normal text-sm">({portfolio?.holdings.length ?? 0} / 5)</span>
        </h2>
        {portfolio?.holdings.length === 0 ? (
          <div className="text-gray-600 text-sm">보유 종목 없음</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  {['티커', '수량', '평균단가', '현재가', '평가금액', '손익률'].map(h => (
                    <th key={h} className="pb-2 pr-6 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {portfolio?.holdings.map(h => (
                  <tr key={h.ticker} className="border-b border-gray-900 hover:bg-gray-900">
                    <td className="py-3 pr-6 font-mono text-blue-300">{h.ticker}</td>
                    <td className="py-3 pr-6">{h.quantity}주</td>
                    <td className="py-3 pr-6">{fmt(h.avg_price)}원</td>
                    <td className="py-3 pr-6">{fmt(h.current_price)}원</td>
                    <td className="py-3 pr-6">{fmt(h.eval_amount)}원</td>
                    <td className="py-3 pr-6">{pct(h.eval_pl_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 진입 후보 */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-1">
          이번 주 진입 후보
        </h2>
        <p className="text-xs text-gray-600 mb-4">기준일: {candidates?.run_date}</p>
        {candidates?.candidates.length === 0 ? (
          <div className="text-gray-600 text-sm">현재 규칙을 충족하는 후보 없음</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  {['종목', '종가', 'MA20 이격', 'RSI', '거래량비', '외국인 5일', '손절가', '목표가'].map(h => (
                    <th key={h} className="pb-2 pr-5 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {candidates?.candidates.map(c => (
                  <tr key={c.ticker} className="border-b border-gray-900 hover:bg-gray-900">
                    <td className="py-3 pr-5">
                      <div className="font-medium">{c.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{c.ticker}</div>
                    </td>
                    <td className="py-3 pr-5">{fmt(c.close)}</td>
                    <td className="py-3 pr-5 text-yellow-400">+{c.ma20_diff_pct}%</td>
                    <td className="py-3 pr-5">{c.rsi}</td>
                    <td className="py-3 pr-5">{c.volume_ratio}x</td>
                    <td className="py-3 pr-5">{fmt(c.foreign_net_5d)}</td>
                    <td className="py-3 pr-5 text-blue-400">{fmt(c.stop_loss)}</td>
                    <td className="py-3 pr-5 text-red-400">{fmt(c.take_profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

    </div>
  )
}
