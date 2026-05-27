import useSWR from 'swr'
import { useState } from 'react'
import { api, PortfolioResponse, CandidatesResponse } from '../api/client'
import {
  PieChart, Pie, Cell, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
} from 'recharts'

function fmt(n: number) { return n.toLocaleString('ko-KR') }

function plColor(n: number) {
  return n > 0 ? 'text-red-400' : n < 0 ? 'text-blue-400' : 'text-gray-400'
}

function PctBadge({ n }: { n: number }) {
  return (
    <span className={`font-semibold ${plColor(n)}`}>
      {n > 0 ? '+' : ''}{n.toFixed(2)}%
    </span>
  )
}

function RsiBadge({ rsi }: { rsi: number }) {
  const cls = rsi >= 55
    ? 'bg-yellow-950 text-yellow-300'
    : rsi <= 40
    ? 'bg-blue-950 text-blue-300'
    : 'bg-emerald-950 text-emerald-300'
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-mono ${cls}`}>{rsi}</span>
  )
}

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b']

const RULES = {
  maxPositions: 5,
  minKrw: 500_000,
  maxKrw: 1_000_000,
  minCashRatio: 0.20,
}

interface RecommendedQty {
  qty: number
  amount: number
}

function calcRecommendedQty(
  entryPrice: number,
  cash: number,
  total: number,
  currentPositions: number
): RecommendedQty | 'full' | 'insufficient' {
  if (currentPositions >= RULES.maxPositions) return 'full'
  const investable = cash - total * RULES.minCashRatio
  if (investable <= 0) return 'insufficient'
  const perPosition = Math.min(RULES.maxKrw, investable)
  if (perPosition < RULES.minKrw) return 'insufficient'
  const qty = Math.floor(perPosition / entryPrice)
  if (qty === 0) return 'insufficient'
  return { qty, amount: qty * entryPrice }
}

interface OrderModal {
  ticker: string; name: string; side: 'buy' | 'sell'; price: number; maxQty?: number
}

const TOOLTIP_STYLE = { background: '#111827', border: '1px solid #374151', borderRadius: '6px' }

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
  const totalPl = s?.total_pl ?? 0
  const totalPlPct = s?.total_pl_pct ?? 0

  return (
    <div className="space-y-8">

      {orderMsg && (
        <div className="rounded border border-gray-700 bg-gray-900 px-4 py-3 text-sm flex justify-between items-center">
          <span className="text-gray-300">{orderMsg}</span>
          <button onClick={() => setOrderMsg('')} className="text-gray-500 hover:text-white ml-4">✕</button>
        </div>
      )}

      {/* 총 자산 */}
      <section>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-5">
          <div className="flex items-start justify-between mb-5">
            <div>
              <div className="text-xs text-gray-500 mb-1">총 자산</div>
              <div className="text-3xl font-bold text-gray-100">
                {fmt(s?.total ?? 0)}<span className="text-xl text-gray-500 ml-1">원</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-0.5 rounded border border-gray-700 text-gray-400">{mode}</span>
              <span className={`text-sm font-semibold px-2 py-1 rounded ${totalPlPct > 0 ? 'bg-red-950 text-red-400' : totalPlPct < 0 ? 'bg-blue-950 text-blue-400' : 'bg-gray-800 text-gray-400'}`}>
                {totalPlPct > 0 ? '+' : ''}{totalPlPct.toFixed(2)}%
              </span>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-gray-800 pt-4">
            <div>
              <div className="text-xs text-gray-500">주식</div>
              <div className="mt-1 text-sm font-semibold text-gray-200">{fmt(s?.total_eval ?? 0)}원</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">현금</div>
              <div className="mt-1 text-sm font-semibold text-gray-200">{fmt(s?.cash ?? 0)}원</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">현금 비중</div>
              <div className="mt-1 text-sm font-semibold text-gray-200">{s?.cash_ratio ?? 100}%</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">손익</div>
              <div className={`mt-1 text-sm font-semibold ${plColor(totalPl)}`}>
                {totalPl > 0 ? '+' : ''}{fmt(totalPl)}원
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 차트 */}
      {pieData.length > 0 && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">포지션 비중</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}
                  label={({ name }) => name ?? ''}>
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => `${fmt(Number(v))}원`} contentStyle={TOOLTIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">종목별 수익률</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 12 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
                <Tooltip
                  formatter={(v) => { const n = Number(v); return `${n > 0 ? '+' : ''}${n.toFixed(2)}%` }}
                  contentStyle={TOOLTIP_STYLE}
                />
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
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-200">보유 종목</h2>
          <span className="text-xs text-gray-500">{portfolio?.holdings.length ?? 0} / 5</span>
        </div>
        {!portfolio ? (
          <div className="text-gray-600 text-sm">불러오는 중...</div>
        ) : portfolio.holdings.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-8 text-center text-sm text-gray-600">보유 종목 없음</div>
        ) : (
          <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-800">
                  {['종목', '수량', '매수가', '현재가', '평가액', '수익률', '손절가', '목표가', ''].map(h => (
                    <th key={h} className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {portfolio.holdings.map(h => (
                  <tr key={h.ticker} className="hover:bg-gray-950 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-gray-100">{h.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{h.ticker}</div>
                    </td>
                    <td className="py-3 px-4 text-gray-300">{h.quantity}주</td>
                    <td className="py-3 px-4 text-gray-300">{fmt(h.avg_price)}</td>
                    <td className="py-3 px-4 text-gray-300">{fmt(h.current_price)}</td>
                    <td className="py-3 px-4 text-gray-300">{fmt(h.eval_amount)}</td>
                    <td className="py-3 px-4"><PctBadge n={h.eval_pl_pct} /></td>
                    <td className="py-3 px-4 text-blue-400 font-mono text-xs">{fmt(h.stop_loss)}</td>
                    <td className="py-3 px-4 text-red-400 font-mono text-xs">{fmt(h.take_profit)}</td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => {
                          setModal({ ticker: h.ticker, name: h.name, side: 'sell', price: h.current_price, maxQty: h.quantity })
                          setQty(h.quantity)
                        }}
                        className="text-xs px-2 py-1 rounded border border-blue-800 text-blue-400 hover:bg-blue-950 transition-colors"
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
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-200">이번 주 진입 후보</h2>
          <span className="text-xs text-gray-500">기준일: {candidates?.run_date ?? '—'}</span>
        </div>
        {!candidates ? (
          <div className="text-gray-600 text-sm">불러오는 중...</div>
        ) : candidates.candidates.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-8 text-center text-sm text-gray-600">현재 규칙을 충족하는 후보 없음</div>
        ) : (
          <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-800">
                  {['종목', '종가', 'MA20', 'RSI', '거래량', '외국인', '손절가', '목표가', '매수 수량', ''].map(h => (
                    <th key={h} className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {candidates.candidates.map(c => (
                  <tr key={c.ticker} className="hover:bg-gray-950 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-gray-100">{c.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{c.ticker}</div>
                    </td>
                    <td className="py-3 px-4 text-gray-300">{fmt(c.close)}</td>
                    <td className="py-3 px-4">
                      <span className="text-yellow-400 text-xs font-mono">+{c.ma20_diff_pct}%</span>
                    </td>
                    <td className="py-3 px-4"><RsiBadge rsi={c.rsi} /></td>
                    <td className="py-3 px-4 text-gray-300 text-xs font-mono">{c.volume_ratio}x</td>
                    <td className="py-3 px-4 text-gray-300 text-xs">{fmt(c.foreign_net_5d)}</td>
                    <td className="py-3 px-4 text-blue-400 font-mono text-xs">{fmt(c.stop_loss)}</td>
                    <td className="py-3 px-4 text-red-400 font-mono text-xs">{fmt(c.take_profit)}</td>
                    <td className="py-3 px-4">
                      {(() => {
                        const rec = calcRecommendedQty(
                          c.entry_price,
                          s?.cash ?? 0,
                          s?.total ?? 0,
                          s?.position_count ?? 0,
                        )
                        if (rec === 'full') return <span className="text-xs text-gray-600">포지션 가득</span>
                        if (rec === 'insufficient') return <span className="text-xs text-gray-600">자금 부족</span>
                        return (
                          <div>
                            <span className="font-semibold text-emerald-400 text-xs">{rec.qty}주</span>
                            <div className="text-xs text-gray-500">≈{fmt(rec.amount)}원</div>
                          </div>
                        )
                      })()}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => {
                          const rec = calcRecommendedQty(c.entry_price, s?.cash ?? 0, s?.total ?? 0, s?.position_count ?? 0)
                          setModal({ ticker: c.ticker, name: c.name, side: 'buy', price: c.entry_price })
                          setQty(typeof rec === 'object' ? rec.qty : 1)
                        }}
                        className="text-xs px-2 py-1 rounded border border-red-800 text-red-400 hover:bg-red-950 transition-colors"
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
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={() => setModal(null)}>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-80 space-y-4 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-100">주문 확인</h3>
              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${modal.side === 'buy' ? 'bg-red-950 text-red-400' : 'bg-blue-950 text-blue-400'}`}>
                {modal.side === 'buy' ? '매수' : '매도'}
              </span>
            </div>
            <div className="space-y-2 text-sm text-gray-300">
              <div className="flex justify-between">
                <span className="text-gray-500">종목</span>
                <span>{modal.name} <span className="text-gray-500 font-mono text-xs">({modal.ticker})</span></span>
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
                    ? 'bg-red-800 hover:bg-red-700 text-white'
                    : 'bg-blue-800 hover:bg-blue-700 text-white'
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
