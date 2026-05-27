import useSWR from 'swr'
import { api, Order } from '../api/client'

function fmt(n: number) { return n.toLocaleString('ko-KR') }

export default function Orders() {
  const { data: orders, isLoading } = useSWR<Order[]>('orders', api.orders, { refreshInterval: 60000 })

  if (isLoading) return <div className="text-gray-500 text-sm">불러오는 중...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200">주문 내역</h2>
        <span className="text-xs text-gray-500">{orders?.length ?? 0}건</span>
      </div>
      {!orders?.length ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-8 text-center text-sm text-gray-600">
          주문 내역이 없습니다.
        </div>
      ) : (
        <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-gray-800">
                {['일시', '종목', '구분', '수량', '체결가', '주문번호'].map(h => (
                  <th key={h} className="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {orders.map(o => (
                <tr key={o.id} className="hover:bg-gray-950 transition-colors">
                  <td className="py-3 px-4 text-gray-400 text-xs">
                    {new Date(o.executed_at).toLocaleString('ko-KR')}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-gray-100">{o.name}</div>
                    <div className="text-xs text-gray-500 font-mono">{o.ticker}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2 py-0.5 rounded font-semibold border ${
                      o.side === 'buy'
                        ? 'bg-red-950 text-red-400 border-red-900'
                        : 'bg-blue-950 text-blue-400 border-blue-900'
                    }`}>
                      {o.side === 'buy' ? '매수' : '매도'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-300">{o.qty}주</td>
                  <td className="py-3 px-4 text-gray-300 font-mono">{fmt(o.price)}원</td>
                  <td className="py-3 px-4 text-xs text-gray-500 font-mono">{o.kis_order_no || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
