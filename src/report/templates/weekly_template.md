# 주간 리포트 {{report_date}}

> 생성: {{generated_at}} | 분석 기준일: {{run_date}}

---

## 1. 포트폴리오 현황

| 항목 | 금액 |
|------|------|
| 총 평가금액 | {{total_assets}} |
| 주식 평가금액 | {{stock_value}} |
| 현금 | {{cash}} |
| 현금 비중 | {{cash_ratio}} |
| 보유 종목 수 | {{position_count}} / {{max_positions}} |

{{#portfolio_violations}}
> ⚠️ 규칙 위반: {{portfolio_violations}}
{{/portfolio_violations}}

{{#halted}}
> 🚨 **일일 손실 한도 도달 — 이번 주 신규 진입 차단**
{{/halted}}

---

## 2. 보유 종목 점검

{{holdings_review}}

---

## 3. 신규 진입 후보

{{candidates_review}}

---

## 4. 리스크 알림

{{risk_summary}}

---

## 5. 사용자 액션 아이템

- [ ] 보유 종목 청산 조건 직접 확인
- [ ] 후보 종목 차트·뉴스 직접 확인
- [ ] 진입 결정 후 모의계좌 우선 시뮬레이션
- [ ] 화요일 장중 분할 매수 (결정 시)
