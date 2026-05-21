"""Claude 시스템/유저 프롬프트 생성."""
import json
from pathlib import Path

import yaml


def _load_rules_yaml() -> str:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "rules.yaml") as f:
        return f.read()


def build_system_prompt() -> str:
    rules_yaml = _load_rules_yaml()
    return f"""당신은 한국 주식 중기 스윙 투자자의 데이터 분석 보조자입니다.

다음 원칙을 반드시 따르십시오:
1. 매수/매도를 단정적으로 추천하지 않습니다. 데이터 패턴을 정리하고, 사용자가 사전에 정한 규칙과의 부합도만 평가합니다.
2. 거시경제 예측, 시장 전체 방향 예측을 하지 않습니다.
3. 데이터에 없는 정보를 추측하지 않습니다. 모르면 "확인 불가"라고 명시합니다.
4. 분석은 간결하게 요점만 작성합니다. 불필요한 수식어를 사용하지 않습니다.
5. 사용자의 투자 규칙(아래)을 기준으로만 점검합니다.

---
사용자 투자 규칙 (rules.yaml):
```yaml
{rules_yaml}
```"""


def build_candidates_prompt(candidates: list[dict], portfolio_status: dict) -> str:
    return f"""## 신규 진입 후보 종목 검토 요청

현재 포트폴리오:
- 보유 종목 수: {portfolio_status['position_count']} / {portfolio_status['max_positions']}
- 현금 비중: {portfolio_status['cash_ratio']:.1%}
- 상태: {portfolio_status['status']}

규칙 엔진이 선별한 후보 종목 {len(candidates)}개:
```json
{json.dumps(candidates, ensure_ascii=False, indent=2)}
```

각 종목에 대해 다음을 간결하게 작성하십시오:
1. 규칙 충족 항목 요약 (수치 포함)
2. 투자자가 직접 확인해야 할 포인트 2~3가지 (차트, 뉴스, 업황 등)
3. 동일 조건의 후보가 여럿일 때 우선순위 제안 (외국인 수급, 재무 건전성 기준)

단정적 매수 추천은 하지 마십시오."""


def build_holdings_prompt(warnings: list[dict], portfolio_status: dict) -> str:
    return f"""## 보유 종목 점검 요청

현재 포트폴리오 상태:
- 총 평가금액: {portfolio_status['total_assets']:,.0f}원
- 현금: {portfolio_status['cash']:,.0f}원 ({portfolio_status['cash_ratio']:.1%})
- 규칙 위반: {portfolio_status['violations'] or '없음'}

청산 조건 충족·근접 종목:
```json
{json.dumps(warnings, ensure_ascii=False, indent=2)}
```

각 종목에 대해:
1. 청산 조건 충족 여부와 해당 조건 명시
2. 청산 조건에 근접한 경우 (±2%) 주의 필요 항목 표시
3. 보유 유지 시 확인해야 할 사항

단정적 매도 추천은 하지 마십시오."""
