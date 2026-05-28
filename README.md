# sehyun-trading

한국 주식 중기 스윙 투자 보조 시스템 — 규칙 기반 신호 생성, Claude AI 주간 리포트, 백테스트, KIS API 연동을 통합한 개인용 투자 분석 도구.

> **투자 주의:** 본 시스템은 의사결정 보조 도구이며 자동 매매를 수행하지 않습니다. 모든 매매는 사용자가 직접 판단하고 집행합니다.

---

## 주요 기능

- **규칙 엔진** — `rules.yaml`에 정의된 진입/청산 조건(MA, RSI, 수급, 거래량)을 자동 점검
- **Claude AI 주간 리포트** — 매주 월요일 후보 종목 분석 및 포트폴리오 코멘트 생성
- **백테스트** — backtrader 기반, 현행 규칙과 개선 후보 비교 리포트
- **KIS API 연동** — 모의투자(VTS) 및 실전 계좌 잔고 조회, 주문 전송
- **멀티유저** — JWT 인증, 사용자별 KIS 자격증명 암호화 저장
- **실시간 대시보드** — 포트폴리오 현황, 주문 히스토리, 성과 차트 (30초 폴링)
- **운영 자동화** — 평일 18:00 데이터 수집, 월요일 07:00 리포트 생성, 일일 S3 백업

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.12, FastAPI, uvicorn, Alembic |
| 데이터 | KIS Developers REST API, pykrx, pandas, pandas-ta |
| 저장소 | PostgreSQL 15 (EC2), Parquet (백테스트) |
| LLM | Claude API (`claude-sonnet-4-6`) |
| 백테스트 | backtrader |
| 프론트엔드 | Vite, React 18, TypeScript, Tailwind CSS |
| 인프라 | AWS EC2 (t3.micro), Vercel, Cloudflare DNS, Let's Encrypt |
| 인증/보안 | JWT, bcrypt, Fernet 암호화, slowapi rate limiting |
| 모니터링 | Sentry, GitHub Actions CI/CD |

---

## 아키텍처

```
Vercel (React SPA)
  ↕ HTTPS
api.sehyun0518.dev (Cloudflare DNS)
  ↕
EC2 (Amazon Linux 2023)
  ├── nginx + SSL
  ├── FastAPI + uvicorn (systemd)
  ├── cron: daily_collect (평일 18:00), weekly_report (월 07:00)
  └── PostgreSQL 15
        │
        ├── KIS Developers API (paper / real)
        └── Claude API (Sonnet 4.6)
```

---

## 로컬 실행

### 사전 요구사항

- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- Node.js 18+
- PostgreSQL 15 (또는 Docker)

### 환경변수 설정

```bash
cp .env.example .env
# .env에서 아래 값 입력:
# DATABASE_URL, KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO
# ANTHROPIC_API_KEY, JWT_SECRET_KEY, CORS_ORIGINS
```

### 백엔드

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn src.api.main:app --reload
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

---

## 투자 규칙 (`config/rules.yaml`)

진입/청산 조건은 분기 첫 주에만 수정하며, 변경 시 백테스트가 필수입니다.

| 구분 | 조건 |
|---|---|
| 종목 유니버스 | KOSPI/KOSDAQ, 시총 3,000억+, 관리종목 제외 |
| 포지션 | 최대 5종목, 종목당 50~100만원, 현금 비중 20% 유지 |
| 진입 (AND) | 종가 > MA20, RSI 30~55, 외국인 5일 순매수 +, 거래량 5일비 1.2x |
| 청산 (OR) | 수익 +15%, 손실 -7%, 보유 60일, MA60 하향 이탈 |
| 리스크 | 일일 -3% 시 그 주 신규 진입 차단 |

---

## 프로젝트 구조

```
sehyun-trading/
├── config/            # rules.yaml, universe.yaml, settings.yaml
├── src/
│   ├── api/           # FastAPI 엔드포인트, JWT 인증
│   ├── data/          # KIS API 래퍼, pykrx 수집기, PostgreSQL I/O
│   ├── rules/         # 규칙 엔진 (universe, signals, portfolio, engine)
│   ├── analysis/      # Claude API 클라이언트, 프롬프트
│   ├── report/        # 주간 리포트 생성
│   └── backtest/      # backtrader 전략, 실행기
├── frontend/          # Vite + React SPA
├── scripts/           # cron 스크립트, 백테스트 실행, DB 초기화
├── deploy/            # systemd, nginx, logrotate 설정
├── alembic/           # DB 마이그레이션
└── docs/              # 전략 백테스트, 실험 결과 문서
```

---

## 운영 스케줄

| 시점 | 스크립트 | 내용 |
|---|---|---|
| 평일 18:00 (KST) | `daily_collect.py` | OHLCV/재무/수급 수집, 잔고 동기화 |
| 월요일 07:00 (KST) | `weekly_report.py` | Claude 주간 리포트 생성 |
| 매일 03:00 (UTC) | `backup_db.py` | pg_dump → S3 |

---

## 비용 (월 기준)

| 항목 | 비용 |
|---|---|
| EC2 t3.micro | ~11,000원 |
| Claude API (Sonnet 4.6, 주 1회) | ~3,000~10,000원 |
| S3 백업, 도메인 | ~1,700원 |
| Vercel / Cloudflare / Sentry | 무료 |
| **합계** | **약 15,700~22,700원/월** |

---

## 면책 고지

본 시스템은 투자 보조 도구이며 투자 결과에 대한 책임은 사용자 본인에게 있습니다. 타인의 자금을 운용하는 용도로 사용할 수 없습니다 (투자일임업 해당).
