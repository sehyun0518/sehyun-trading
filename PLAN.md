# 한국 주식 중기 스윙 투자 보조 시스템 (KR Swing Advisor)

## 0. 프로젝트 개요

### 목적
한국 주식 중기 스윙(주~월 단위) 투자에 필요한 데이터 수집·분석·리포트를 자동화하여, **사용자의 의사결정을 보조**하는 시스템. MVP 단계에서는 본인 1인용으로 시작했으나, 현재는 **다중 사용자 공개 서비스**로 확장 중이다.

### 핵심 원칙
- **Claude는 분석 도구이지 의사결정자가 아니다.** 모든 매매는 사용자 판단·집행.
- **결정론적 데이터 파이프라인 + 비결정론적 분석 레이어**를 분리한다. LLM은 분석에만 관여.
- **규칙 기반 투자.** 사용자가 사전에 정한 `rules.yaml` 규칙을 시스템이 점검·집행.
- **단계적 자본 투입.** 모의투자 → 소액 실전 → 점진 증액.
- **모의투자는 KIS API 통해 실제 주문**까지 진행 (paper 계좌), 실전 모드는 별도 자격증명.

### 비목표 (Non-Goals)
- 자동 매매·자동 주문 (사용자 명시 동의 없이는 금지)
- 단타·스캘핑 지원
- 거시경제·시장 전체 방향 예측
- 투자일임업 (타인 자금 운용 불가; 각 사용자는 본인 KIS 계정 사용)

---

## 1. 현재 상태 (MVP 완료)

### ✅ 완료된 영역
| 영역 | 상태 |
|---|---|
| 데이터 수집 (KIS + pykrx) | ✅ 완료 |
| 규칙 엔진 (rules.yaml 기반) | ✅ 완료 |
| Claude 주간 리포트 | ✅ 완료 |
| backtrader 백테스트 | ✅ 완료 |
| 모의투자 KIS 실제 주문 연동 | ✅ 완료 |
| FastAPI 백엔드 (EC2) | ✅ 완료 |
| Vite + React 프론트엔드 (Vercel) | ✅ 완료 |
| PostgreSQL 마이그레이션 | ✅ 완료 |
| 도메인 + HTTPS (api.sehyun0518.dev) | ✅ 완료 |
| 모의/실전 모드 런타임 전환 UI | ✅ 완료 |

### ⚠️ 알려진 결함 (확장 전 해결 필요)
- API 인증 부재 (누구나 `/api/portfolio`, `/api/mode` 호출 가능)
- CORS 전체 허용 (`allow_origins=["*"]`)
- KIS 자격증명 `.env` 평문 저장
- 단일 유저 가정 (DB에 `user_id` 없음)
- 백업 없음
- 모니터링 없음
- 테스트 디렉토리 비어있음

---

## 2. 시스템 아키텍처

### 현재 (MVP)
```
┌─────────────────────────────────────────────────────┐
│  Vercel (Vite + React SPA)                          │
│  ↕ HTTPS                                            │
│  api.sehyun0518.dev (Cloudflare DNS only)           │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────┼──────────────────────────────────┐
│  EC2 (Amazon Linux 2023, t3.micro)                  │
│  ┌────────────┐  │   ┌──────────────────────────┐  │
│  │  nginx     │──┘   │  systemd                 │  │
│  │  + SSL     ├──────┤  sehyun-trading.service  │  │
│  └────────────┘      │  (FastAPI + uvicorn)     │  │
│                      └──────────┬───────────────┘  │
│  ┌────────────────────────────┐ │                  │
│  │  cron (trading user)       │ │                  │
│  │  - daily_collect (18:00)   │ │                  │
│  │  - weekly_report (월 07:00)│ │                  │
│  └──────────┬─────────────────┘ │                  │
│             ▼                    ▼                  │
│         ┌─────────────────────────┐                 │
│         │  PostgreSQL 15          │                 │
│         │  (단일 유저 데이터)     │                 │
│         └─────────────────────────┘                 │
└─────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
   KIS Developers API         Claude API
   (paper / real)             (Sonnet 4.6)
```

### 목표 (Phase 1~3 완료 후)
```
+ 변경점:
- nginx 앞단에 JWT 인증 미들웨어
- users 테이블 + bcrypt password
- KIS 자격증명 Fernet 암호화 후 DB 저장
- S3 자동 백업 (일일)
- Sentry 모니터링
- GitHub Actions 자동 배포
```

### 기술 스택
- **백엔드**: Python 3.12, FastAPI, uvicorn, psycopg2-binary
- **데이터**: KIS Developers REST API, pykrx, pandas
- **저장소**: PostgreSQL 15 (EC2), Parquet (백테스트)
- **분석**: pandas, pandas-ta, numpy
- **LLM**: Claude API (`claude-sonnet-4-6`)
- **백테스트**: backtrader
- **프론트엔드**: Vite, React 18, TypeScript, Tailwind, react-router-dom
- **인프라**: AWS EC2, Vercel, Cloudflare DNS, Let's Encrypt
- **스케줄링**: cron (EC2)

---

## 3. 프로젝트 구조

```
sehyun-trading/
├── PLAN.md                          # 본 문서
├── README.md
├── pyproject.toml                   # Python 의존성 (uv)
├── .env.example                     # 환경변수 템플릿
├── .gitignore                       # *.pem, .env, 토큰 캐시 제외
│
├── config/
│   ├── rules.yaml                   # ★ 사용자 투자 규칙
│   ├── universe.yaml                # 종목 유니버스 정의
│   └── settings.yaml                # 시스템 설정
│
├── src/
│   ├── api/                         # ★ FastAPI 백엔드
│   │   ├── main.py                  # 엔드포인트 정의
│   │   └── auth.py                  # (Phase 1) JWT 미들웨어
│   ├── data/
│   │   ├── kis_client.py            # KIS API 래퍼 (paper/real)
│   │   ├── pykrx_collector.py       # pykrx 수집기
│   │   └── storage.py               # PostgreSQL/SQLite I/O
│   ├── rules/
│   │   ├── universe.py
│   │   ├── signals.py
│   │   ├── portfolio.py
│   │   └── engine.py
│   ├── analysis/
│   │   ├── claude_client.py
│   │   ├── prompts.py
│   │   └── reviewer.py
│   ├── report/
│   │   └── weekly.py
│   └── backtest/
│       ├── strategy.py
│       └── runner.py
│
├── frontend/                        # ★ Vite + React SPA
│   ├── src/
│   │   ├── App.tsx                  # 모드 토글 헤더
│   │   ├── api/client.ts            # API 호출 + JWT 토큰 관리
│   │   └── pages/
│   │       ├── Dashboard.tsx
│   │       ├── Reports.tsx
│   │       ├── Login.tsx            # (Phase 1)
│   │       ├── Signup.tsx           # (Phase 2)
│   │       └── Settings.tsx         # (Phase 2)
│   ├── vercel.json                  # SPA 라우팅
│   └── vite.config.ts
│
├── scripts/
│   ├── daily_collect.py             # 평일 18:00 EC2 cron
│   ├── weekly_report.py             # 월 07:00 EC2 cron
│   ├── update_holdings.py           # 수동 매매 (KIS 실제 주문)
│   ├── setup_db.py                  # DB 스키마 초기화
│   └── run_backtest.py              # 백테스트
│
├── deploy/                          # ★ EC2 배포
│   ├── setup_ec2.sh                 # AL2023 프로비저닝
│   ├── sehyun-trading.service       # systemd 유닛
│   └── nginx.conf                   # 리버스 프록시
│
├── data/                            # gitignore
└── tests/                           # 비어 있음 (개선 필요)
```

---

## 4. 데이터 모델 (PostgreSQL)

```sql
-- 시계열 데이터 (기존)
daily_ohlcv (ticker, date, open, high, low, close, volume, value) PK(ticker, date)
ticker_info (ticker PK, name, market, sector, market_cap, updated_at)
fundamentals (ticker, date, per, pbr, eps, bps, div_yield, roe) PK(ticker, date)
trading_flow (ticker, date, foreign_net, inst_net, indiv_net) PK(ticker, date)
holdings    (ticker PK, quantity, avg_price, current_price, eval_amount, eval_pl, eval_pl_pct, updated_at)
reports     (report_date PK, candidates JSON, warnings JSON, file_path, content TEXT)

-- Phase 2 추가 예정
users       (id PK, email UNIQUE, password_hash, created_at,
             kis_paper_key_enc, kis_paper_secret_enc, kis_paper_account,
             kis_real_key_enc,  kis_real_secret_enc,  kis_real_account,
             notify_slack_webhook, notify_discord_webhook)
holdings_snapshots (user_id, date, ticker, ...)  -- 성과 차트용
orders      (id PK, user_id, ticker, side, qty, price, executed_at, kis_order_no)

-- Phase 2 변경 예정
* 기존 시계열 테이블 중 holdings/reports에 user_id FK 추가
```

---

## 5. 운영 스케줄

| 시점 | 실행 | 내용 |
|------|------|------|
| 평일 18:00 (EC2 cron) | `daily_collect.py` | OHLCV/재무/수급 수집, 잔고 동기화 |
| 월요일 07:00 (EC2 cron) | `weekly_report.py` | 주간 리포트 생성, DB 저장 |
| 매일 03:00 (Phase 3) | `pg_dump → S3` | DB 백업 |
| 푸시 트리거 (Phase 3) | GitHub Actions | EC2 자동 배포 |

---

## 6. 단계별 구현 로드맵

### ✅ Phase 1~6: MVP 구축 (완료)
- 데이터 수집 / 규칙 엔진 / Claude 분석 / 리포트 / 백테스트 / 모의투자 KIS 연동
- FastAPI 백엔드 + React 프론트엔드 / EC2 + Vercel 배포 / 도메인 + HTTPS

### ✅ Phase 7: 긴급 보안 강화 (완료)

**Why:** 현재 API는 인증 없이 외부 노출. `/api/mode`로 모드 전환까지 가능.

- [x] 7-1. CORS 화이트리스트 (`CORS_ORIGINS` 환경변수)
- [x] 7-2. JWT 인증 미들웨어 (`/api/health` 외 전부 토큰 필수)
- [ ] 7-3. KIS 자격증명 Fernet 암호화 (DB 저장) → Phase 8 users 테이블과 함께 진행
- [x] 7-4. slowapi rate limiting (분당 60회)
- [x] 7-5. 토큰 캐시 파일 권한 600, .env 600

**수정 파일:** `src/api/main.py`, `src/api/auth.py` (신규), `src/data/kis_client.py`, `src/data/secrets.py` (신규), `pyproject.toml`, `frontend/src/pages/Login.tsx`, `frontend/src/api/client.ts`

### ✅ Phase 8: 멀티유저 기반 (완료)

**Why:** 공개 서비스에서 각 사용자가 본인 KIS 계정으로 사용해야 한다.

- [x] 8-1. `users` 테이블 신설, `holdings`/`reports`에 `user_id` FK 추가
- [x] 8-2. Alembic 도입 (0001 초기 스키마 / 0002 Phase8 마이그레이션)
- [x] 8-3. 회원가입/로그인 페이지 + KIS 자격증명 설정 페이지
- [x] 8-4. `kis_client.get_holdings(user_creds)` per-user 자격증명 지원
- [x] 8-5. storage 함수 `user_id` 인자화 (holdings, reports)

### ✅ Phase 9: 운영 안정성 (완료)

**Why:** 공개 서비스는 죽으면 안 된다.

- [x] 9-1. PostgreSQL 일일 `pg_dump` → S3 (`scripts/backup_db.py`, 03:00 UTC cron)
- [x] 9-2. Sentry 초기화 (`SENTRY_DSN` 환경변수, FastAPI 시작 시 자동 연동)
- [x] 9-3. GitHub Actions CI/CD (`main` push 시 자동 배포, `.github/workflows/deploy.yml`)
- [ ] 9-4. UptimeRobot 헬스체크 — `https://api.sehyun0518.dev/api/health` 5분 간격 수동 등록
- [x] 9-5. 로그 영구화 (`deploy/logrotate.conf`, 30일 보존)

### ✅ Phase 10: UX 핵심 기능 (4주차)

- [x] 10-1. 대시보드 30초 폴링 (SWR)
- [x] 10-2. 매수/매도 웹 UI (확인 모달)
- [x] 10-3. 주문 히스토리 페이지 (/orders)
- [x] 10-4. 성과 차트 (recharts: 종목 비중 파이·손익률 바)
- [x] 10-5. Slack/Discord webhook 알림 (주문 체결)

### 🟡 Phase 11: 공개 접근성 + 온보딩 (진행 중)

**Why:** 일반 사용자가 가입 전 서비스 목적, 투자 보조 범위, 현재 전략의 한계를 이해할 수 있어야 한다.

- [x] 11-1. 비로그인 공개 홈 추가 (`/`)
- [x] 11-2. 로그인 후 기본 진입 경로를 `/dashboard`로 분리
- [x] 11-3. 신규 가입 후 `Settings`에서 KIS 자격증명 입력까지 이어지는 온보딩 체크리스트
- [x] 11-4. 약관·개인정보처리방침·투자 유의사항 페이지
- [x] 11-5. 유입 사용자의 회원가입/실사용 전환을 위한 히어로 카피·CTA 개선
- [x] 11-6. 가입 후 흐름·대상 사용자·핵심 기능·하단 CTA를 포함한 메인 콘텐츠 확장
- [x] 11-7. 카드 나열형 메인 섹션을 타임라인·행 리스트·기능 표 중심 정보 구조로 개선
- [x] 11-8. 모바일 주요 레이아웃 반응형 보강
- [ ] 11-9. Lighthouse 모바일 90+ 검증
- [ ] 11-10. Cloudflare Proxied 활성화 (DDoS 보호)

**수정 파일:** `frontend/src/App.tsx`, `frontend/src/pages/PublicHome.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/Legal.tsx`

### ⚪ Phase 12: 전략 검증 + 지표 개선

**Why:** 현재 지표 조합으로 2주 운영 후 수익성이 확인되지 않았다. 규칙 변경은 감이 아니라 백테스트, 실거래 로그, 실패 케이스 분류를 근거로 해야 한다.

- [x] 12-1. 최근 2주 주문/보유 로그를 기준으로 후보 선정 당시 지표 스냅샷 저장
- [x] 12-2. 현행 규칙(`MA20`, `RSI 30~55`, 외국인 5일 순매수, 거래량비 1.2x)의 최근 6~12개월 백테스트 재실행
- [ ] 12-3. 실패 후보 분류: 추세 역행, 거래량 착시, 수급 지속 실패, 시장/섹터 약세, 손절 지연
- [ ] 12-4. 대체/보강 지표 후보 실험: MA20 기울기, MA60 정렬, 상대강도, ATR 변동성, 기관 수급, 시장 지수 필터
- [ ] 12-5. 변경 전후 승률, 평균 손익비, MDD, 보유기간, 거래빈도 비교 리포트 생성
- [ ] 12-6. 검증된 경우에만 `rules.yaml` 개정. 변경일, 근거, 백테스트 결과를 리포트에 남김

**수정 파일:** `alembic/versions/0004_candidate_snapshots.py`, `src/api/main.py`, `src/data/storage.py`, `src/backtest/runner.py`, `scripts/setup_db.py`, `scripts/run_backtest.py`, `frontend/src/api/client.ts`, `docs/phase12-strategy-backtest.md`

### ⚪ Phase 13: 실투자 진입 (지속)

- [ ] 100만원 소액 시작 → 1개월 정상 운영 확인
- [ ] 200만원 증액 → 추가 1~2개월
- [ ] 분기마다 규칙 재검토, 백테스트 재실행

---

## 7. 리스크 및 안전장치

### 기술적 안전장치
- KIS 토큰은 디스크 캐시 (`data/.kis_token_*.json`, 600 권한) — 1분 재발급 제한 우회
- 초당 20회 KIS rate limit 슬라이딩 윈도우 준수
- 모의(VTS) URL과 실전 URL 분리, 시장 데이터는 항상 실전 자격증명
- 일일 손실 -3% 도달 시 그 주 신규 진입 차단 (`rules.yaml`)
- 데이터 수집 실패 시 리포트 생성 중단

### 인지적 함정 방지
- **Claude 의존 방지**: 격주로 Claude 코멘트 없이 데이터만 보고 판단 훈련
- **규칙 변경 제약**: `rules.yaml`은 분기 첫 주에만 변경, 변경 시 백테스트 의무
- **충동 매매 차단**: 매수/매도 UI에 확인 모달, 손절가/목표가 자동 계산 표시

### 법적·세무
- 본인 자금 한정 (투자일임업 등록 대상이므로 타인 자금 운용 금지)
- 거래 내역은 KIS 거래내역 + 자체 `orders` 테이블 (Phase 10)에 보관
- 약관에 책임 제한 명시 (Phase 11)

---

## 8. 비용 추정 (월 단위)

| 항목 | 비용 |
|---|---|
| EC2 t3.micro (free tier 종료 후) | ~11,000원 |
| 도메인 `.dev` (연 환산) | ~1,500원 |
| S3 백업 (5GB 미만) | ~200원 |
| Claude API (Sonnet 4.6, 주 1회) | ~3,000~10,000원 |
| Sentry / Vercel / Cloudflare / UptimeRobot | 무료 |
| **합계** | **약 15,700~22,700원/월** |

t4g.nano 다운사이즈 시 약 4,500원으로 절감 가능.

---

## 9. 검증 방법 (Phase별)

**Phase 7 (보안):**
- `curl https://api.sehyun0518.dev/api/portfolio` → `401 Unauthorized`
- 다른 도메인에서 fetch → CORS 차단
- Sentry에 의도적 에러 → 캡처 확인

**Phase 8 (멀티유저):**
- 두 테스트 계정 생성, 각자 다른 KIS 키, 데이터 격리 확인
- Alembic `upgrade head → downgrade -1` 왕복

**Phase 9 (운영):**
- 더미 커밋 → 1분 내 자동 배포
- S3 백업 → `pg_restore` 성공
- 서비스 중단 → UptimeRobot 알림

**Phase 10 (UX):**
- UI 매수 → KIS Developer Portal에서 체결 확인
- 손절가 도달 시뮬레이션 → Slack 알림

**Phase 11~12:**
- Lighthouse 모바일 90+
- 신규 가입 → 사용 → 백테스트 전체 흐름 통과

---

## 10. 성공 기준

본 시스템의 성공은 **수익률이 아니라 프로세스 준수**로 평가한다.

- ✅ 사용자가 매주 리포트를 검토하고, 규칙에 어긋난 충동 매매를 하지 않음
- ✅ 백테스트와 모의투자 결과 괴리 ±5%p 이내
- ✅ Claude 리포트가 의사결정에 실질 기여 (주관 평가)
- ✅ 공개 서비스 단계: 신규 가입 → 첫 리포트 수신까지 5분 이내
- ✅ 가동률 99.5% 이상 (월 다운타임 3.6시간 이하)

수익률은 부차적 지표. 시장은 통제할 수 없지만 프로세스는 통제할 수 있다.

---

## 11. 다음 단계

상세 확장 로드맵은 `~/.claude/plans/inherited-cuddling-parasol.md`에 별도 보관.

**즉시 진행:** Phase 11-9 Lighthouse 모바일 검증과 Phase 12-3 서버 주문/스냅샷 기반 실패 후보 분류를 병행한다. 로컬 백테스트에서는 `market_cap` 데이터 품질 문제가 확인되었으므로, 시가총액 데이터 정상화도 함께 진행한다.
