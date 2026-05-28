---
name: 지표 피드백
about: RSI, MA, 수급 등 현재 지표 조합의 문제점이나 대안 지표를 제안해 주세요
title: "[지표] "
labels: indicator
assignees: sehyun0518
---

## 현재 지표 조합

```yaml
entry_signal:
  close_above_ma: 20              # 종가 > 20일 이동평균
  rsi_range: [30, 55]             # RSI 30~55
  foreign_net_5d_positive: true   # 최근 5일 외국인 순매수 양수
  volume_ratio_5d: 1.2            # 거래량 5일 평균의 1.2배
```

## 문제점 또는 제안

<!-- 현재 지표의 어떤 부분이 한국 시장에서 잘 작동하지 않는지, 또는 추가하면 좋을 지표가 무엇인지 알려주세요 -->

## 대안 제안 (선택)

<!-- 구체적인 지표나 파라미터 값이 있으면 함께 제안해 주세요 -->

## 참고 자료 (선택)
