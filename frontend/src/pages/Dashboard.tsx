import useSWR from 'swr'
import { useState } from 'react'
import { api, PortfolioResponse, CandidatesResponse } from '../api/client'
import {
  PieChart, Pie, Cell, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
} from 'recharts'

function fmt(n: number) { return n.toLocaleString('ko-KR') }
function pct(n: number) {
  const color = n > 0 ? 'text-red-400' : n < 0 ? 'text-blue-400' : 'text-gray-400'
  return <span className={color}>{n > 0 ? '+' : ''}{n.toFixed(2)}%</span>
}

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b']

interface OrderModal {
  ticker: string; name: string; side: 'buy' | 'sell'; price: number; maxQty?: number
}

export default function Dashboard() {
  const { data: portfolio } = useSWR<PortfolioResponse>('portfolio', api.portfolio, { refreshInterval: 30000 })
  const { data: candidates } = useSWR<CandidatesResponse>('candidates', api.candidates, { refreshInterval: 30000 })
  const [modal, setModal] = useState<OrderModal | null>(null)
  const [qty, setQty] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [orderMsg, setOrderMsg] = useState('')

  async function submitOrder() {
    if (!modal) return
    setSubmitting(true)
    try {
      await api.placeOrder({ ticker: modal.ticker, name: modal.name, side: modal.side, qty })
      setOrderMsg(`${modal.side === 'buy' ? '매수' : '매도'} 완료: ${modal.name} ${qty}주`)
      setModal(null)
    } catch (e: unknown) {
      setOrderMsg(`주문 실패: ${e instanceof Error ? e.message : '알 수 없는 오류'}`)
    } finally {
      setSubmitting(false)
    }
  }

  const s = portfolio?.summary
  const mode = portfolio?.mode === 'paper' ? '모의투자' : '실전투자'
  const pieData = portfolio?.holdings.map(h => ({ name: h.name || h.ticker, value: h.eval_amount })) ?? []
  const barData = portfolio?.holdings.map(h => ({ name: h.name || h.ticker, pct: h.eval_pl_pct })) ?? []

  return (
    <div className="space-y-8">

      {orderMsg && (
        <div className="bg-gray-800 border border-gray-700 rounded px-4 py-3 text-sm flex justify-between">
          <span>{orderMsg}</span>
          <button onClick={() => setOrderMsg('')} className="text-gray-500 hover:text-white ml-4">✕</button>
        </div>
      )}

      {/* 포트폴리오 요약 */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-base font-semibold text-gray-200">포트폴리오 현황</h2>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">{mode}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
          {[
            { label: '총평가금액', value: `${fmt(s?.total ?? 0)}원` },
            { label: '주식평가금액', value: `${fmt(s?.total_eval ?? 0)}원` },
            { label: '현금', value: `${fmt(s?.cash ?? 0)}원` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <div className="text-xs text-gray-500 mb-1">{label}</div>
              <div className="text-lg font-semibold">{value}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <div className="text-xs text-gray-500 mb-1">현금비중</div>
            <div className="text-lg font-semibold">{s?.cash_ratio ?? 100}%</div>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <div className="text-xs text-gray-500 mb-1">전체 손익금액</div>
            <div className={`text-lg font-semibold ${(s?.total_pl ?? 0) > 0 ? 'text-red-400' : (s?.total_pl ?? 0) < 0 ? 'text-blue-400' : ''}`}>
              {(s?.total_pl ?? 0) > 0 ? '+' : ''}{fmt(s?.total_pl ?? 0)}원
            </div>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <div className="text-xs text-gray-500 mb-1">전체 손익률</div>
            <div className={`text-lg font-semibold ${(s?.total_pl_pct ?? 0) > 0 ? 'text-red-400' : (s?.total_pl_pct ?? 0) < 0 ? 'text-blue-400' : ''}`}>
              {(s?.total_pl_pct ?? 0) > 0 ? '+' : ''}{(s?.total_pl_pct ?? 0).toFixed(2)}%
            </div>
          </div>
        </div>
      </section>

      {/* 차트 */}
      {pieData.length > 0 && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-400 mb-3">포지션 비중</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}
                  label={({ name }) => name ?? ''}>
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => `${fmt(Number(v))}원`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-400 mb-3">종목별 손익률 (%)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <Tooltip formatter={(v) => { const n = Number(v); return `${n > 0 ? '+' : ''}${n.toFixed(2)}%` }} />
                <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={entry.pct >= 0 ? '#ef4444' : '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* 보유 종목 */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-4">
          보유 종목 <span className="text-gray-500 font-normal text-sm">({portfolio?.holdings.length ?? 0} / 5)</span>
        </h2>
        {!portfolio ? (
          <div className="text-gray-600 text-sm">불러오는 중...</div>
        ) : portfolio.holdings.length === 0 ? (
          <div className="text-gray-600 text-sm">보유 종목 없음</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  {['종목', '수량', '평균단가', '현재가', '평가금액', '손익률', ''].map(h => (
                    <th key={h} className="pb-2 pr-6 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {portfolio.holdings.map(h => (
                  <tr key={h.ticker} className="border-b border-gray-900 hover:bg-gray-900">
                    <td className="py-3 pr-6">
                      <div className="font-medium">{h.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{h.ticker}</div>
                    </td>
                    <td className="py-3 pr-6">{h.quantity}주</td>
                    <td className="py-3 pr-6">{fmt(h.avg_price)}원</td>
                    <td className="py-3 pr-6">{fmt(h.current_price)}원</td>
                    <td className="py-3 pr-6">{fmt(h.eval_amount)}원</td>
                    <td className="py-3 pr-6">{pct(h.eval_pl_pct)}</td>
                    <td className="py-3">
                      <button
                        onClick={() => {
                          setModal({ ticker: h.ticker, name: h.ticker, side: 'sell', price: h.current_price, maxQty: h.quantity })
                          setQty(h.quantity)
                        }}
                        className="text-xs px-2 py-1 rounded bg-blue-900 text-blue-300 hover:bg-blue-800 transition-colors"
                      >매도</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 진입 후보 */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-1">이번 주 진입 후보</h2>
        <p className="text-xs text-gray-600 mb-4">기준일: {candidates?.run_date ?? '—'}</p>
        {!candidates ? (
          <div className="text-gray-600 text-sm">불러오는 중...</div>
        ) : candidates.candidates.length === 0 ? (
          <div className="text-gray-600 text-sm">현재 규칙을 충족하는 후보 없음</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  {['종목', '종가', 'MA20 이격', 'RSI', '거래량비', '외국인 5일', '손절가', '목표가', ''].map(h => (
                    <th key={h} className="pb-2 pr-5 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {candidates.candidates.map(c => (
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
                    <td className="py-3">
                      <button
                        onClick={() => {
                          setModal({ ticker: c.ticker, name: c.name, side: 'buy', price: c.entry_price })
                          setQty(1)
                        }}
                        className="text-xs px-2 py-1 rounded bg-red-900 text-red-300 hover:bg-red-800 transition-colors"
                      >매수</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 주문 확인 모달 */}
      {modal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-80 space-y-4" onClick={e => e.stopPropagation()}>
            <h3 className="font-semibold text-gray-100">
              {modal.side === 'buy' ? '매수' : '매도'} 주문 확인
            </h3>
            <div className="space-y-2 text-sm text-gray-300">
              <div className="flex justify-between">
                <span className="text-gray-500">종목</span>
                <span>{modal.name} ({modal.ticker})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">구분</span>
                <span className={modal.side === 'buy' ? 'text-red-400' : 'text-blue-400'}>
                  {modal.side === 'buy' ? '매수' : '매도'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">예상가</span>
                <span>{fmt(modal.price)}원</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">수량</span>
                <input
                  type="number" min={1} max={modal.maxQty ?? 9999} value={qty}
                  onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-right text-sm"
                />
              </div>
              <div className="flex justify-between font-medium pt-2 border-t border-gray-800">
                <span className="text-gray-500">예상 금액</span>
                <span>{fmt(modal.price * qty)}원</span>
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setModal(null)}
                className="flex-1 py-2 rounded border border-gray-700 text-gray-400 hover:text-white text-sm transition-colors"
              >취소</button>
              <button
                onClick={submitOrder}
                disabled={submitting}
                className={`flex-1 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 ${
                  modal.side === 'buy'
                    ? 'bg-red-700 hover:bg-red-600 text-white'
                    : 'bg-blue-700 hover:bg-blue-600 text-white'
                }`}
              >
                {submitting ? '처리 중...' : modal.side === 'buy' ? '매수 확인' : '매도 확인'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
