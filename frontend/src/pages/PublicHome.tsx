import { Link } from 'react-router-dom'

const hasToken = () => Boolean(localStorage.getItem('auth_token'))

const heroStats = [
  { label: '시작 방식', value: '모의투자 우선' },
  { label: '판단 기준', value: '규칙 + 기록' },
  { label: '전략 상태', value: '검증 진행 중' },
]

const productRows = [
  { label: '오늘 확인할 후보', value: '3종목', tone: 'text-green-300' },
  { label: '보유 종목 경고', value: '1건', tone: 'text-yellow-300' },
  { label: '저장된 검증 스냅샷', value: '자동', tone: 'text-blue-300' },
]

const trustItems = [
  'KIS 자격증명은 암호화해 저장하고, 원문을 다시 노출하지 않습니다.',
  '후보 선정 당시 지표를 저장해 수익이 나지 않은 이유를 나중에 분석합니다.',
  '서비스는 매매를 대신 결정하지 않으며, 실전투자는 사용자가 직접 확인 후 실행합니다.',
]

const workflows = [
  {
    step: '01',
    title: 'KIS 모의투자 계정 연결',
    description: '처음부터 실전 계좌를 연결하지 않아도 됩니다. 모의투자 자격증명으로 후보 조회와 주문 흐름을 먼저 확인합니다.',
  },
  {
    step: '02',
    title: '이번 주 후보와 보유 종목 점검',
    description: 'MA20, RSI, 거래량, 외국인 수급 조건을 통과한 후보와 보유 종목의 손절·목표가를 한 화면에서 봅니다.',
  },
  {
    step: '03',
    title: '주문 전 수량과 기준가 확인',
    description: '추천 수량, 손절가, 목표가를 확인한 뒤 사용자가 직접 매수·매도 실행 여부를 결정합니다.',
  },
  {
    step: '04',
    title: '성과가 안 난 이유를 기록으로 검토',
    description: '후보 선정 당시 지표 스냅샷과 주문 기록을 남겨 다음 백테스트와 규칙 개선의 근거로 사용합니다.',
  },
]

const features = [
  { title: '후보 종목 필터링', description: '정해진 규칙을 모두 통과한 종목만 후보로 보여줍니다.' },
  { title: '보유 종목 경고', description: '손절, 목표가, 이동평균 이탈 등 청산 검토 조건을 표시합니다.' },
  { title: '주문 기록 관리', description: '매수·매도 실행 내역을 사용자별로 저장해 사후 분석에 사용합니다.' },
  { title: '주간 리포트', description: '후보, 경고, 시장 데이터를 정리해 반복 가능한 검토 루틴을 만듭니다.' },
  { title: '전략 스냅샷', description: '후보가 나온 순간의 지표를 저장해 결과와 비교할 수 있게 합니다.' },
  { title: '모의/실전 분리', description: '모의투자에서 흐름을 확인한 뒤 실전 계정은 별도로 연결합니다.' },
]

const audiences = [
  '매주 같은 기준으로 한국 주식 후보를 좁히고 싶은 투자자',
  '감정적인 추격 매수와 늦은 손절을 줄이고 싶은 사용자',
  '모의투자로 전략 흐름을 검증한 뒤 실전으로 넘어가고 싶은 사용자',
]

export default function PublicHome() {
  const signedIn = hasToken()

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-5 py-4">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <Link to="/" className="text-lg font-bold text-blue-400">KR Swing Advisor</Link>
          <div className="ml-auto flex items-center gap-2">
            {signedIn ? (
              <Link className="rounded border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:border-gray-500 hover:text-white" to="/dashboard">
                대시보드
              </Link>
            ) : (
              <>
                <Link className="rounded border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:border-gray-500 hover:text-white" to="/login">
                  로그인
                </Link>
                <Link className="rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700" to="/signup">
                  시작하기
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <section className="border-b border-gray-900">
          <div className="mx-auto grid max-w-6xl gap-10 px-5 py-10 lg:grid-cols-[1fr_480px] lg:py-14">
            <div className="flex flex-col justify-center">
              <div className="mb-4 inline-flex w-fit rounded border border-blue-900 bg-blue-950/40 px-3 py-1 text-xs font-medium text-blue-300">
                KIS 모의투자 계정으로 먼저 검증
              </div>
              <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-white md:text-5xl">
                감으로 고른 종목을 줄이고, 매주 같은 기준으로 점검하세요
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-gray-400">
                KR Swing Advisor는 한국 주식 중기 스윙 투자자를 위해 후보 종목, 보유 종목 경고, 손절·목표가, 주문 기록을 한 흐름으로 정리합니다.
                성과가 나지 않은 지표도 숨기지 않고 저장해 다음 전략 점검에 사용합니다.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link className="rounded bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700" to={signedIn ? '/dashboard' : '/signup'}>
                  {signedIn ? '내 대시보드 열기' : '모의투자로 시작하기'}
                </Link>
                <Link className="rounded border border-gray-700 px-5 py-3 text-sm font-medium text-gray-300 hover:border-gray-500 hover:text-white" to="/legal/risk">
                  투자 유의사항 보기
                </Link>
              </div>
              <div className="mt-6 grid max-w-xl grid-cols-3 gap-3">
                {heroStats.map(item => (
                  <div key={item.label} className="border-l border-gray-800 pl-3">
                    <div className="text-xs text-gray-500">{item.label}</div>
                    <div className="mt-1 text-sm font-semibold text-gray-200">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 shadow-2xl shadow-black/30">
              <div className="mb-4 flex items-center justify-between border-b border-gray-800 pb-3">
                <div>
                  <div className="text-sm font-semibold text-gray-100">가입 후 첫 화면</div>
                  <div className="text-xs text-gray-500">계정 연결 후 개인 데이터로 갱신</div>
                </div>
                <span className="rounded bg-yellow-950 px-2 py-1 text-xs text-yellow-300">모의투자</span>
              </div>
              <div className="grid grid-cols-3 divide-x divide-gray-800 border-y border-gray-800">
                {productRows.map(item => (
                  <div key={item.label} className="bg-gray-950 px-3 py-4">
                    <div className="text-xs text-gray-500">{item.label}</div>
                    <div className={`mt-1 text-lg font-semibold ${item.tone}`}>{item.value}</div>
                  </div>
                ))}
              </div>
              <div className="mt-5 overflow-hidden border border-gray-800">
                {[
                  { name: '후보 A', status: '진입 기준 통과', detail: 'RSI 48 · 거래량 1.4x' },
                  { name: '보유 B', status: '손절가 근접', detail: '현재 -5.8% · 기준 -7%' },
                  { name: '전략 기록', status: '스냅샷 저장', detail: '후보 지표와 체크 결과 보관' },
                ].map(row => (
                  <div key={row.name} className="grid grid-cols-[90px_1fr] items-center gap-3 border-b border-gray-800 bg-gray-950 px-3 py-3 text-sm last:border-b-0">
                    <span className="font-medium text-gray-100">{row.name}</span>
                    <span>
                      <span className="block text-gray-200">{row.status}</span>
                      <span className="text-xs text-gray-500">{row.detail}</span>
                    </span>
                  </div>
                ))}
              </div>
              <Link
                className="mt-5 block rounded bg-gray-100 px-4 py-3 text-center text-sm font-semibold text-gray-950 hover:bg-white"
                to={signedIn ? '/dashboard' : '/signup'}
              >
                {signedIn ? '대시보드로 이동' : '계정 만들고 연결 시작'}
              </Link>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-8 px-5 py-10 md:grid-cols-[360px_1fr]">
          <div>
            <h2 className="text-xl font-semibold text-white">가입 전에 확인할 것</h2>
            <p className="mt-3 text-sm leading-6 text-gray-500">
              투자 판단을 대신하는 서비스가 아니라, 사용자가 같은 기준을 반복해서 점검하도록 돕는 도구입니다.
            </p>
          </div>
          <div className="divide-y divide-gray-800 border-y border-gray-800">
            {trustItems.map((item, index) => (
              <div key={item} className="grid gap-3 py-4 md:grid-cols-[120px_1fr]">
                <div className="text-xs font-semibold text-blue-300">확인 {index + 1}</div>
                <div className="text-sm leading-6 text-gray-300">{item}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="border-y border-gray-900 bg-gray-950 px-5 py-10">
          <div className="mx-auto max-w-6xl">
            <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">가입 후 실제 흐름</h2>
                <p className="mt-2 text-sm text-gray-500">계정 생성부터 전략 점검까지 한 번의 루틴으로 이어집니다.</p>
              </div>
              <Link className="w-fit rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700" to={signedIn ? '/dashboard' : '/signup'}>
                {signedIn ? '대시보드 열기' : '이 흐름으로 시작하기'}
              </Link>
            </div>
            <div className="relative grid gap-0 border-y border-gray-800 md:grid-cols-4 md:border-x">
              {workflows.map(item => (
                <div key={item.step} className="border-b border-gray-800 px-4 py-5 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
                  <div className="text-xs font-semibold text-blue-300">{item.step}</div>
                  <h3 className="mt-3 text-sm font-semibold text-gray-100">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-gray-500">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[320px_1fr]">
          <div>
            <h2 className="text-xl font-semibold text-white">어떤 사용자에게 맞는가</h2>
            <p className="mt-3 text-sm leading-6 text-gray-500">
              수익을 보장하는 도구가 아니라, 반복 가능한 투자 검토 습관을 만드는 도구입니다.
            </p>
          </div>
          <div className="space-y-0 border-y border-gray-800">
            {audiences.map((item, index) => (
              <div key={item} className="grid gap-3 border-b border-gray-800 py-4 last:border-b-0 md:grid-cols-[140px_1fr]">
                <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">사용자 {index + 1}</div>
                <div className="text-sm leading-6 text-gray-300">{item}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t border-gray-900 px-5 py-10">
          <div className="mx-auto max-w-6xl">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white">핵심 기능</h2>
              <p className="mt-2 text-sm text-gray-500">후보 선정, 주문 보조, 기록, 검증을 하나의 화면 흐름으로 묶습니다.</p>
            </div>
            <div className="overflow-x-auto border-y border-gray-800">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-xs uppercase tracking-wider text-gray-500">
                    <th className="py-3 pr-6 font-semibold">기능</th>
                    <th className="py-3 pr-6 font-semibold">사용자가 얻는 것</th>
                    <th className="py-3 font-semibold">가입 후 위치</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((item, index) => (
                    <tr key={item.title} className="border-b border-gray-900 last:border-b-0">
                      <td className="py-4 pr-6 font-medium text-gray-100">{item.title}</td>
                      <td className="py-4 pr-6 leading-6 text-gray-400">{item.description}</td>
                      <td className="py-4 text-gray-500">
                        {index < 2 ? '대시보드' : index < 4 ? '주문·리포트' : '전략 검증'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="border-y border-blue-950 bg-blue-950/20 px-5 py-8">
          <div className="mx-auto flex max-w-6xl flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <h2 className="text-xl font-semibold text-white">먼저 모의투자로 확인하세요</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100/70">
                현재 전략은 검증 단계입니다. 계정을 만들고 KIS 모의투자를 연결한 뒤, 후보가 어떻게 나오고 기록이 어떻게 쌓이는지 확인하는 것부터 시작하세요.
              </p>
            </div>
            <Link className="inline-flex min-h-11 w-full shrink-0 items-center justify-center rounded bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 sm:w-fit" to={signedIn ? '/dashboard' : '/signup'}>
              {signedIn ? '대시보드로 이동' : '계정 만들기'}
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-gray-900 px-5 py-6">
        <div className="mx-auto flex max-w-6xl flex-wrap gap-4 text-xs text-gray-500">
          <Link className="hover:text-gray-300" to="/legal/terms">이용약관</Link>
          <Link className="hover:text-gray-300" to="/legal/privacy">개인정보처리방침</Link>
          <Link className="hover:text-gray-300" to="/legal/risk">투자 유의사항</Link>
        </div>
      </footer>
    </div>
  )
}
