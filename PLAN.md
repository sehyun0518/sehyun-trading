# 한국 주식 중기 스윙 투자 보조 시스템 (KR Swing Advisor)

## 0. 프로젝트 개요

### 목적
한국 주식 중기 스윙(주~월 단위) 투자에 필요한 데이터 수집·분석·리포트를 자동화하여, **사용자의 의사결정을 보조**하는 시스템을 구축한다. 실제 매매 주문은 사용자가 수동으로 집행한다.

### 핵심 원칙
- **Claude는 분석 도구이지 의사결정자가 아니다.** 모든 매매는 사용자 판단·집행.
- **결정론적 데이터 파이프라인 + 비결정론적 분석 레이어**를 분리한다. LLM은 분석에만, 데이터 수집에는 일절 관여시키지 않는다.
- **규칙 기반 투자.** 사용자가 사전에 정한 규칙을 시스템이 점검·집행하는 구조이며, Claude가 규칙을 만들지 않는다.
- **단계적 자본 투입.** 500만원 일괄 투입 금지. 모의 8주 → 100만원 → 점진 증액.

### 비목표 (Non-Goals)
- 자동 매매·자동 주문 (절대 금지)
- 단타·스캘핑 지원
- 거시경제·시장 전체 방향 예측
- 타인 자금 운용 (투자일임업 등록 대상이므로 본인 자금 한정)

---

## 1. 시스템 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│                      Data Collection Layer                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   │
│  │  KIS API     │   │   pykrx      │   │  News RSS (opt)  │   │
│  │ (시세/잔고)  │   │ (재무/수급)  │   │ (보유종목 뉴스)  │   │
│  └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘   │
│         └──────────────────┼─────────────────────┘             │
│                            ▼                                    │
│              ┌──────────────────────────┐                       │
│              │  SQLite (시계열 저장)    │                       │
│              │  data/market.db          │                       │
│              └────────────┬─────────────┘                       │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                  Analysis Layer (Weekly)                        │
│                            ▼                                    │
│              ┌──────────────────────────┐                       │
│              │  Rule Engine (Python)    │                       │
│              │  - 종목 유니버스 필터   │                       │
│              │  - 진입/청산 시그널     │                       │
│              │  - 포트폴리오 점검      │                       │
│              └────────────┬─────────────┘                       │
│                           ▼                                     │
│              ┌──────────────────────────┐                       │
│              │  Claude API (Sonnet 4.6) │                       │
│              │  - 정형 데이터 해석     │                       │
│              │  - 후보 종목 리뷰       │                       │
│              │  - 리스크 점검          │                       │
│              └────────────┬─────────────┘                       │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                    Reporting Layer                              │
│                            ▼                                    │
│              ┌──────────────────────────┐                       │
│              │  주간 리포트 (Markdown)  │                       │
│              │  reports/YYYY-MM-DD.md   │                       │
│              └────────────┬─────────────┘                       │
│                           ▼                                     │
│                    [사용자 검토]                                │
│                           ▼                                     │
│                    [수동 주문 집행]                             │
└─────────────────────────────────────────────────────────────────┘
```

### 기술 스택
- **언어**: Python 3.11+
- **데이터 수집**: KIS Developers REST API, pykrx
- **저장소**: SQLite (시계열), Parquet (백테스트용 대용량 데이터)
- **분석**: pandas, numpy, ta-lib (또는 pandas-ta)
- **LLM**: Claude API (`claude-sonnet-4-6`)
- **백테스트**: backtrader
- **스케줄링**: cron (Linux/Mac) 또는 Task Scheduler (Windows)
- **리포트**: Markdown → 로컬 폴더 (선택: Notion API 연동)

---

## 2. 프로젝트 구조

```
sehyun-trading/
├── plan.md                          # 본 문서
├── README.md
├── pyproject.toml                   # 의존성 (uv 또는 poetry)
├── .env.example                     # 환경변수 템플릿
├── .gitignore
│
├── config/
│   ├── rules.yaml                   # ★ 사용자 투자 규칙 (가장 중요)
│   ├── universe.yaml                # 종목 유니버스 정의
│   └── settings.yaml                # 시스템 설정
│
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── kis_client.py            # KIS API 래퍼 (조회 전용)
│   │   ├── pykrx_collector.py       # pykrx 수집기
│   │   ├── news_collector.py        # (선택) RSS 수집기
│   │   └── storage.py               # SQLite I/O
│   │
│   ├── rules/
│   │   ├── universe.py              # 종목 유니버스 필터링
│   │   ├── signals.py               # 진입/청산 시그널 계산
│   │   ├── portfolio.py             # 포트폴리오 비중·리스크 점검
│   │   └── engine.py                # 규칙 통합 엔진
│   │
│   ├── analysis/
│   │   ├── claude_client.py         # Claude API 래퍼
│   │   ├── prompts.py               # 시스템/유저 프롬프트
│   │   └── reviewer.py              # 후보 종목 리뷰 로직
│   │
│   ├── report/
│   │   ├── weekly.py                # 주간 리포트 생성
│   │   ├── templates/
│   │   │   └── weekly_template.md
│   │   └── notion.py                # (선택) Notion 업로드
│   │
│   ├── backtest/
│   │   ├── strategy.py              # backtrader 전략 정의
│   │   └── runner.py                # 백테스트 실행기
│   │
│   └── utils/
│       ├── logging.py
│       └── dates.py                 # 한국 거래일 처리
│
├── scripts/
│   ├── daily_collect.py             # 매일 16:00 데이터 수집
│   ├── weekly_report.py             # 일요일 19:00 리포트 생성
│   ├── run_backtest.py              # 수동 백테스트 실행
│   └── setup_db.py                  # 초기 DB 스키마 생성
│
├── data/
│   ├── market.db                    # SQLite (gitignore)
│   └── parquet/                     # 백테스트용 (gitignore)
│
├── reports/
│   └── YYYY-MM-DD-weekly.md         # 주간 리포트 누적 (gitignore)
│
└── tests/
    ├── test_kis_client.py
    ├── test_signals.py
    └── test_rules.py
```

---

## 3. 데이터 모델

### SQLite 스키마

```sql
-- 일봉 OHLCV
CREATE TABLE daily_ohlcv (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      INTEGER,
    value       INTEGER,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX idx_ohlcv_date ON daily_ohlcv(date);

-- 종목 기본 정보 (시총, 섹터)
CREATE TABLE ticker_info (
    ticker      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    market      TEXT,        -- KOSPI / KOSDAQ
    sector      TEXT,
    market_cap  INTEGER,
    updated_at  TIMESTAMP
);

-- 재무 지표 (분기 단위)
CREATE TABLE fundamentals (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    per         REAL,
    pbr         REAL,
    eps         REAL,
    bps         REAL,
    div_yield   REAL,
    roe         REAL,
    PRIMARY KEY (ticker, date)
);

-- 수급 (외국인/기관/개인 순매수)
CREATE TABLE trading_flow (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    foreign_net REAL,
    inst_net    REAL,
    indiv_net   REAL,
    PRIMARY KEY (ticker, date)
);

-- 보유 종목 (KIS API에서 일일 동기화)
CREATE TABLE holdings (
    ticker      TEXT PRIMARY KEY,
    quantity    INTEGER,
    avg_price   REAL,
    current_price REAL,
    eval_amount INTEGER,
    eval_pl     INTEGER,
    eval_pl_pct REAL,
    updated_at  TIMESTAMP
);

-- 주간 리포트 메타데이터
CREATE TABLE reports (
    report_date DATE PRIMARY KEY,
    candidates  TEXT,       -- JSON: 추천 후보 종목
    warnings    TEXT,       -- JSON: 보유 종목 경고
    file_path   TEXT
);
```

---

## 4. 핵심 모듈 상세

### 4.1 데이터 수집 (`src/data/`)

**`kis_client.py`** — 한국투자증권 KIS Developers REST API 래퍼
- **권한 제한 토큰**: 조회 전용으로만 사용. 주문 권한이 있는 토큰은 생성하지 않는다.
- 주요 메서드:
  - `get_holdings()` → 잔고 조회
  - `get_quote(ticker)` → 현재가
  - `get_daily_ohlcv(ticker, start, end)` → 일봉 (백업용; 주로 pykrx 사용)
- 토큰 만료 시 자동 갱신
- Rate limit: 초당 20건 이하 (KIS 제한 준수)

**`pykrx_collector.py`** — pykrx 라이브러리 래퍼
- `collect_universe_ohlcv(date)` → 코스피200+코스닥150 일봉
- `collect_fundamentals(date)` → PER/PBR/배당수익률
- `collect_trading_flow(ticker, days)` → 외국인·기관 순매수
- 모든 함수는 멱등 (같은 날짜 재실행 시 UPSERT)

**`storage.py`** — SQLite I/O
- `upsert_ohlcv(df)`, `get_ohlcv(ticker, start, end)`, `get_universe()` 등
- 트랜잭션 단위로 묶어 일관성 보장

### 4.2 규칙 엔진 (`src/rules/`)

**핵심: `config/rules.yaml`이 시스템의 헌법이다.** 모든 규칙은 이 파일에서 읽어온다. 코드에 하드코딩하지 않는다.

```yaml
# config/rules.yaml 예시 (사용자가 직접 작성/수정)
universe:
  markets: [KOSPI, KOSDAQ]
  min_market_cap_billion: 300       # 시총 3,000억 이상
  exclude_sectors: [관리종목, 환기종목]
  exclude_themes: []

position:
  max_positions: 5                  # 최대 보유 종목 수
  position_size_min_krw: 500_000
  position_size_max_krw: 1_000_000
  min_cash_ratio: 0.20              # 최소 현금 비중 20%
  max_sector_weight: 0.40           # 1섹터 최대 40%

entry_signal:                       # AND 조건
  - close_above_ma: 20              # 20일 이평선 위
  - rsi_range: [30, 55]
  - foreign_net_5d_positive: true
  - volume_ratio_5d: 1.2            # 5일 평균 대비 1.2배 이상

exit_signal:                        # OR 조건
  take_profit_pct: 15
  stop_loss_pct: -7
  time_stop_days: 60
  ma_break: 60                      # 60일선 하향 이탈

risk:
  daily_loss_halt_pct: -3.0         # 일일 -3% 시 그 주 중단
  weekly_loss_review_pct: -5.0
```

**`universe.py`** — rules.yaml 기준으로 종목 유니버스 필터링
**`signals.py`** — 기술적 지표 계산 (이동평균, RSI, 거래량 비율)
**`portfolio.py`** — 현재 보유 종목의 비중·섹터·수익률 점검
**`engine.py`** — 위 세 모듈 통합. 산출물:
- `candidates`: 진입 조건 충족 종목 리스트
- `warnings`: 보유 종목 중 청산 조건 충족 또는 근접 종목
- `portfolio_status`: 현재 비중·현금 상태

### 4.3 Claude 분석 레이어 (`src/analysis/`)

**철학**: Claude에게는 "이 종목 사야 할까?"가 아니라 **"이 데이터를 해석해줘"**를 묻는다.

**`prompts.py`** — 시스템 프롬프트 구성
```
당신은 한국 주식 중기 스윙 투자자의 데이터 분석 보조자다.
다음 규칙을 따른다:

1. 매수/매도 추천을 단정적으로 하지 않는다. 데이터 패턴을 정리하고,
   사용자가 사전에 정한 규칙과의 부합도만 평가한다.
2. 거시경제 예측, 시장 전체 방향 예측을 하지 않는다.
3. 데이터에 없는 정보를 추측하지 않는다. 모르면 모른다고 한다.
4. 사용자의 투자 규칙(첨부)을 기준으로 점검한다.

사용자의 투자 규칙:
<rules.yaml 내용 삽입>
```

**`reviewer.py`** — 주요 함수:
```python
def review_candidates(candidates: list[dict], market_context: dict) -> str:
    """규칙 엔진이 뽑은 후보 종목 N개에 대해
    재무·수급·기술적 지표를 정리하고 사용자가 검토할 포인트를 제시"""

def review_holdings(holdings: list[dict], warnings: list[dict]) -> str:
    """보유 종목 현황 점검. 청산 조건 근접 종목 강조"""
```

**모델 선택**: `claude-sonnet-4-6` (균형). 주 1회 호출이므로 비용 무시 가능 수준.

### 4.4 리포트 (`src/report/`)

**주간 리포트 템플릿** (일요일 19:00 자동 생성):

```markdown
# 주간 리포트 YYYY-MM-DD

## 1. 포트폴리오 현황
- 총 평가금액: X원 (현금 Y원, 주식 Z원)
- 주간 수익률: ±X%
- 보유 종목별 손익

## 2. 보유 종목 점검 (Rule Engine)
- 청산 조건 충족: [종목 리스트]
- 청산 조건 근접 (±2%): [종목 리스트]
- Claude 코멘트

## 3. 신규 진입 후보 (Rule Engine + Claude 리뷰)
- 후보 1: 종목명 (티커)
  - 진입 조건 충족 항목
  - 재무·수급 요약
  - Claude 점검 결과
  - 진입가/손절가 가이드 (규칙 기반 계산)
- 후보 2, 3...

## 4. 리스크 알림
- 일일 -3% 도달 여부
- 섹터 편중 여부

## 5. 사용자 액션 아이템 (체크리스트)
- [ ] 보유 종목 청산 검토
- [ ] 후보 종목 차트 직접 확인
- [ ] 진입 결정 후 모의계좌 우선 시뮬레이션
- [ ] 화요일 장중 분할 매수
```

### 4.5 백테스트 (`src/backtest/`)

**`strategy.py`** — backtrader Strategy 클래스로 `rules.yaml` 규칙을 구현
**`runner.py`** — CLI로 실행:
```bash
python scripts/run_backtest.py \
    --start 2020-01-01 --end 2024-12-31 \
    --capital 5000000 \
    --rules config/rules.yaml
```
산출: 누적 수익률, MDD, 샤프, 승률, 거래 횟수, 종목별 기여도

---

## 5. 운영 스케줄

| 시점 | 실행 스크립트 | 내용 |
|------|--------------|------|
| 평일 16:00 | `daily_collect.py` | 일봉·재무·수급 수집, 잔고 동기화 |
| 일요일 19:00 | `weekly_report.py` | 주간 리포트 생성 |
| 월요일 (수동) | — | 사용자 리포트 검토, 결정 |
| 화요일 장중 (수동) | — | 사용자 직접 주문 |
| 분기 첫 주 (수동) | `run_backtest.py` | 규칙 재검증 |

cron 예시:
```
0 16 * * 1-5  cd /path/to/kr-swing-advisor && uv run python scripts/daily_collect.py
0 19 * * 0    cd /path/to/kr-swing-advisor && uv run python scripts/weekly_report.py
```

---

## 6. 단계별 구현 로드맵

### Phase 1: 환경 구축 (Day 1~2)
- [ ] 프로젝트 초기화 (`uv init`, 디렉토리 구조)
- [ ] `.env`, `settings.yaml`, `rules.yaml` 템플릿 작성
- [ ] SQLite 스키마 생성 (`scripts/setup_db.py`)
- [ ] KIS Developers 가입 → 앱키·시크릿 발급 → 조회 전용 토큰 (사용자 수동)
- [ ] 모의계좌 개설 (사용자 수동)

### Phase 2: 데이터 수집 (Day 3~5)
- [ ] `kis_client.py` — 토큰 발급/갱신, 잔고 조회, 시세 조회
- [ ] `pykrx_collector.py` — 일봉/재무/수급 수집기
- [ ] `storage.py` — SQLite UPSERT
- [ ] `scripts/daily_collect.py` — 통합 수집 파이프라인
- [ ] **검증**: 1주일 수동 실행하며 데이터 정합성 확인

### Phase 3: 규칙 엔진 (Day 6~9)
- [ ] `rules.yaml` 초안 작성 (★ 사용자 의사결정 필요)
- [ ] `signals.py` — 이동평균, RSI, 거래량 비율 계산 + 단위 테스트
- [ ] `universe.py`, `portfolio.py`, `engine.py`
- [ ] **검증**: 과거 한 시점 데이터로 후보 종목이 합리적으로 나오는지 점검

### Phase 4: Claude 분석 + 리포트 (Day 10~12)
- [ ] `claude_client.py`, `prompts.py`
- [ ] `reviewer.py` — 후보·보유 리뷰
- [ ] `weekly.py` + 템플릿
- [ ] **검증**: 더미 데이터로 리포트 1건 생성 → 사용자가 직접 읽고 유용성 평가

### Phase 5: 백테스트 (Day 13~17)
- [ ] `backtest/strategy.py` — rules.yaml 규칙을 backtrader로 이식
- [ ] `backtest/runner.py`
- [ ] **검증**: 2020~2024 5년 백테스트 실행
- [ ] **Go/No-Go 결정**: 백테스트 결과 부적절하면 Phase 3로 돌아가 규칙 재설계

### Phase 6: 모의투자 (Week 4~12, 최소 8주)
- [ ] cron 등록
- [ ] 매주 일요일 리포트 검토 → 모의계좌 주문
- [ ] 주간 회고: Claude 리포트와 사용자 판단 일치도, 시스템 오류, 데이터 누락
- [ ] 8주 누적 후 평가:
  - 모의 수익률이 백테스트와 큰 괴리가 있는가?
  - 시스템이 안정적으로 돌아가는가?
  - Claude 리포트가 실제로 의사결정에 기여하는가?

### Phase 7: 실투자 시작 (Week 13~)
- [ ] **100만원**으로 시작 (500만원 일괄 투입 금지)
- [ ] 1개월 정상 운영 확인 → 200만원 증액
- [ ] 추가 1~2개월 후 사용자 판단으로 잔여 자금 투입
- [ ] 분기마다 규칙 재검토, 백테스트 재실행

---

## 7. 리스크 및 안전장치

### 기술적 안전장치
- KIS API 토큰은 **조회 전용**. 주문 API 호출 코드 자체를 작성하지 않는다.
- `rules.yaml` 변경 이력은 git으로 추적. 손실 직후 충동적 변경 방지.
- 일일 손실 -3% 도달 시 자동으로 그 주 신규 진입 차단 (리포트에 명시).
- 데이터 수집 실패 시 리포트 생성 중단 (불완전 데이터로 판단 금지).

### 인지적 함정 방지
- **Claude 의존 방지**: 매주 리포트의 Claude 코멘트 부분을 무시하고 데이터만 보고 판단하는 훈련을 격주로 수행한다.
- **규칙 변경 제약**: `rules.yaml`은 분기 첫 주에만 변경. 변경 시 백테스트 의무.
- **수동 주문 원칙**: 어떤 자동화 유혹이 와도 주문은 사용자가 증권사 앱·HTS에서 직접.

### 법적·세무
- 본인 자금 한정. 타인 자금 운용 금지 (투자일임업 등록 대상).
- 거래 내역은 별도 가계부 또는 증권사 거래내역으로 보관, 연말 양도세 신고 자료로 활용.

---

## 8. 비용

| 항목 | 비용 |
|------|------|
| KIS Developers | 무료 |
| pykrx | 무료 (오픈소스) |
| Claude API (Sonnet 4.6, 주 1회) | ~$5–20/월 |
| 인프라 (로컬 cron) | $0 |
| **월 합계** | **~$10–25** |

---

## 9. 성공 기준

본 시스템의 성공은 **수익률이 아니라 프로세스 준수**로 평가한다.

- ✅ 8주 모의투자 기간 동안 시스템이 한 번도 잘못된 데이터를 수집하지 않음
- ✅ 사용자가 매주 리포트를 검토하고, 규칙에 어긋난 충동적 매매를 하지 않음
- ✅ 백테스트와 모의투자 결과의 괴리가 크지 않음 (수익률 ±5%p 이내)
- ✅ Claude 리포트가 사용자의 의사결정에 실질적으로 기여 (주관 평가)

수익률은 부차적 지표. 시장은 통제할 수 없지만 프로세스는 통제할 수 있다.

---

## 10. 다음 단계

이 plan.md를 검토한 뒤, 다음 순서로 진행한다:

1. **Phase 1 환경 구축부터 시작** — 폴더 구조, 의존성, 설정 파일 템플릿 생성
2. **`rules.yaml` 초안 작성** — 사용자가 본인 투자 철학을 명문화 (가장 시간 걸림)
3. Phase 2부터는 코드 작성. Claude(저)가 단계별로 구현해드릴 수 있음.

각 Phase 시작 전에 산출물 명세를 확정하고, 완료 시 검증 기준을 통과해야 다음 Phase로 진행한다.