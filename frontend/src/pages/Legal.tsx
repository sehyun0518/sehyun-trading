import { Link, Navigate, useParams } from 'react-router-dom'

const docs = {
  terms: {
    title: '이용약관',
    body: [
      'KR Swing Advisor는 한국 주식 중기 스윙 투자 판단을 보조하기 위한 데이터·리포트·기록 관리 도구입니다.',
      '서비스가 제공하는 후보 종목, 경고, 리포트, 주문 보조 정보는 투자 권유나 수익 보장을 의미하지 않습니다.',
      '모든 주문 실행 여부와 수량, 가격, 계좌 선택은 사용자 본인의 판단과 책임으로 결정합니다.',
      '사용자는 본인 명의의 KIS 계정만 연결해야 하며, 타인 자금 운용이나 투자일임 목적으로 사용할 수 없습니다.',
    ],
  },
  privacy: {
    title: '개인정보처리방침',
    body: [
      '서비스는 로그인, 계정 식별, KIS API 연동, 알림 전송에 필요한 최소 정보를 저장합니다.',
      'KIS App Key와 App Secret은 서버에서 암호화해 저장하며, 화면에는 원문을 다시 노출하지 않습니다.',
      '주문 내역, 후보 스냅샷, 리포트는 사용자별로 분리 저장되며 전략 검증과 서비스 기능 제공에 사용됩니다.',
      '사용자는 계정 삭제 또는 데이터 삭제가 필요한 경우 운영자에게 요청할 수 있습니다.',
    ],
  },
  risk: {
    title: '투자 유의사항',
    body: [
      '주식 투자는 원금 손실 가능성이 있으며, 과거 백테스트나 모의투자 결과가 미래 수익을 보장하지 않습니다.',
      '현재 지표 조합은 실전 관찰 단계이며, 2026-05-27 기준 최근 2주 운영에서 수익성이 확인되지 않았습니다.',
      '규칙 변경은 충분한 백테스트와 실거래 로그 검토 후 진행해야 하며, 손실 회피를 보장하지 않습니다.',
      '실전투자 전에는 모의투자 흐름, 주문 확인 화면, 손절 기준, 계좌 권한을 반드시 점검해야 합니다.',
    ],
  },
}

type DocKey = keyof typeof docs

export default function Legal() {
  const { doc = 'terms' } = useParams()
  if (!(doc in docs)) return <Navigate to="/legal/terms" replace />

  const current = doc as DocKey
  const item = docs[current]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-5 py-4">
        <div className="mx-auto flex max-w-3xl items-center gap-4">
          <Link to="/" className="text-lg font-bold text-blue-400">KR Swing Advisor</Link>
          <Link to="/signup" className="ml-auto rounded bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors">
            시작하기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-10">
        <div className="mb-6 flex flex-wrap gap-2">
          {Object.entries(docs).map(([key, value]) => (
            <Link
              key={key}
              to={`/legal/${key}`}
              className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                current === key
                  ? 'bg-blue-600 text-white'
                  : 'border border-gray-800 text-gray-400 hover:border-gray-600 hover:text-white'
              }`}
            >
              {value.title}
            </Link>
          ))}
        </div>

        <article className="rounded-lg border border-gray-800 bg-gray-900 p-6">
          <h1 className="text-xl font-semibold text-white">{item.title}</h1>
          <div className="mt-6 divide-y divide-gray-800">
            {item.body.map((paragraph, index) => (
              <div key={index} className="grid gap-3 py-4 first:pt-0 last:pb-0 md:grid-cols-[80px_1fr]">
                <div className="text-xs font-semibold text-blue-300">조항 {index + 1}</div>
                <p className="text-sm leading-7 text-gray-300">{paragraph}</p>
              </div>
            ))}
          </div>
          <p className="mt-6 border-t border-gray-800 pt-4 text-xs text-gray-500">최종 업데이트: 2026-05-27</p>
        </article>
      </main>
    </div>
  )
}
