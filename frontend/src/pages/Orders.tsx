import useSWR from 'swr'
import { api, Order } from '../api/client'

function fmt(n: number) { return n.toLocaleString('ko-KR') }

export default function Orders() {
  const { data: orders, isLoading } = useSWR<Order[]>('orders', api.orders, { refreshInterval: 60000 })

  if (isLoading) return <div className="text-gray-500 text-sm">불러오는 중...</div>

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-gray-200">주문 내역</h2>
      {!orders?.length ? (
        <div className="text-gray-600 text-sm">주문 내역이 없습니다.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800">
                {['일시', '종목', '구분', '수량', '체결가', '주문번호'].map(h => (
                  <th key={h} className="pb-2 pr-6 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id} className="border-b border-gray-900 hover:bg-gray-900">
                  <td className="py-3 pr-6 text-gray-400 text-xs">
                    {new Date(o.executed_at).toLocaleString('ko-KR')}
                  </td>
                  <td className="py-3 pr-6">
                    <div className="font-medium">{o.name}</div>
                    <div className="text-xs text-gray-500 font-mono">{o.ticker}</div>
                  </td>
                  <td className="py-3 pr-6">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                      o.side === 'buy' ? 'bg-red-900 text-red-300' : 'bg-blue-900 text-blue-300'
                    }`}>
                      {o.side === 'buy' ? '매수' : '매도'}
                    </span>
                  </td>
                  <td className="py-3 pr-6">{o.qty}주</td>
                  <td className="py-3 pr-6">{fmt(o.price)}원</td>
                  <td className="py-3 pr-6 text-xs text-gray-500 font-mono">{o.kis_order_no || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
