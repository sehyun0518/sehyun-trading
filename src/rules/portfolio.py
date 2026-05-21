"""보유 포트폴리오 비중·섹터·리스크 점검."""
from pathlib import Path

import pandas as pd
import yaml


def _load_rules() -> dict:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "rules.yaml") as f:
        return yaml.safe_load(f)


def check_portfolio(holdings: pd.DataFrame, ticker_info: pd.DataFrame,
                    cash: float = 0.0) -> dict:
    """
    holdings: storage.get_holdings() 결과
      컬럼: ticker, quantity, avg_price, current_price, eval_amount, eval_pl, eval_pl_pct
    ticker_info: storage.get_universe() — sector 정보용
    cash: 현금 잔고 (원)

    반환: {
        total_assets, stock_value, cash, cash_ratio,
        position_count, max_positions,
        sector_weights: {섹터: 비중},
        violations: [규칙 위반 메시지],
        status: "OK" | "WARNING",
    }
    """
    rules = _load_rules()
    pos = rules["position"]
    result: dict = {}

    stock_value = float(holdings["eval_amount"].sum()) if not holdings.empty else 0.0
    total_assets = stock_value + cash
    cash_ratio = cash / total_assets if total_assets > 0 else 1.0

    result["total_assets"] = total_assets
    result["stock_value"] = stock_value
    result["cash"] = cash
    result["cash_ratio"] = round(cash_ratio, 4)
    result["position_count"] = len(holdings)
    result["max_positions"] = pos.get("max_positions", 5)

    # 섹터 비중 계산
    sector_weights: dict[str, float] = {}
    if not holdings.empty and not ticker_info.empty:
        merged = holdings.merge(
            ticker_info[["ticker", "sector"]], on="ticker", how="left"
        )
        for sector, grp in merged.groupby("sector"):
            w = grp["eval_amount"].sum() / total_assets if total_assets > 0 else 0.0
            sector_weights[str(sector)] = round(w, 4)
    result["sector_weights"] = sector_weights

    # 규칙 위반 체크
    violations: list[str] = []

    if len(holdings) > pos.get("max_positions", 5):
        violations.append(
            f"보유 종목 수 초과: {len(holdings)}/{pos['max_positions']}"
        )

    min_cash = pos.get("min_cash_ratio", 0.20)
    if cash_ratio < min_cash:
        violations.append(
            f"현금 비중 부족: {cash_ratio:.1%} < {min_cash:.0%}"
        )

    max_sector = pos.get("max_sector_weight", 0.40)
    for sector, w in sector_weights.items():
        if w > max_sector:
            violations.append(
                f"섹터 편중: {sector} {w:.1%} > {max_sector:.0%}"
            )

    result["violations"] = violations
    result["status"] = "WARNING" if violations else "OK"
    return result


def can_add_position(portfolio_status: dict, amount: float) -> tuple[bool, str]:
    """신규 종목 진입 가능 여부 판단."""
    rules = _load_rules()
    pos = rules["position"]

    if portfolio_status["position_count"] >= pos.get("max_positions", 5):
        return False, f"최대 보유 종목 수 도달 ({pos['max_positions']}개)"

    min_krw = pos.get("position_size_min_krw", 500_000)
    max_krw = pos.get("position_size_max_krw", 1_000_000)
    if not (min_krw <= amount <= max_krw):
        return False, f"투자금액 범위 초과: {amount:,.0f}원 (허용: {min_krw:,.0f}~{max_krw:,.0f})"

    min_cash_ratio = pos.get("min_cash_ratio", 0.20)
    new_cash = portfolio_status["cash"] - amount
    new_total = portfolio_status["total_assets"]
    new_cash_ratio = new_cash / new_total if new_total > 0 else 0
    if new_cash_ratio < min_cash_ratio:
        return False, f"진입 후 현금 비중 부족: {new_cash_ratio:.1%} < {min_cash_ratio:.0%}"

    return True, "OK"
