"""규칙 통합 엔진 — candidates / warnings / portfolio_status 생성."""
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

from src.data import storage
from src.rules import universe, signals, portfolio

log = logging.getLogger(__name__)


def _load_rules() -> dict:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "rules.yaml") as f:
        return yaml.safe_load(f)


def run(target_date: date | None = None, cash: float = 0.0) -> dict:
    """
    규칙 엔진 전체 실행.

    Parameters
    ----------
    target_date : 분석 기준일 (기본값: 오늘)
    cash        : 현금 잔고 (원). 잔고 API 없을 시 직접 전달.

    Returns
    -------
    {
        "candidates":       [후보 종목 dict, ...],
        "warnings":         [보유 종목 경고 dict, ...],
        "portfolio_status": dict,
        "run_date":         str,
        "halted":           bool,  # 일일 손실 한도 도달 시 True
    }
    """
    target = target_date or date.today()
    rules = _load_rules()

    # ── 1. 포트폴리오 현황 ──────────────────────────────────────────────────
    holdings = storage.get_holdings()
    ticker_info = storage.get_universe()
    portfolio_status = portfolio.check_portfolio(holdings, ticker_info, cash)

    # ── 2. 일일 손실 한도 체크 ───────────────────────────────────────────────
    halt_pct = rules["risk"].get("daily_loss_halt_pct", -3.0)
    # 오늘 평가손익률이 halt_pct 이하면 신규 진입 차단
    daily_pl_pct = 0.0
    if not holdings.empty and "eval_pl_pct" in holdings.columns:
        daily_pl_pct = float(holdings["eval_pl_pct"].mean())
    halted = daily_pl_pct <= halt_pct
    if halted:
        log.warning(f"일일 손실 한도 도달 ({daily_pl_pct:.1f}%) — 신규 진입 차단")

    # ── 3. 보유 종목 청산 조건 점검 (warnings) ──────────────────────────────
    warnings: list[dict] = []
    held_tickers = holdings["ticker"].tolist() if not holdings.empty else []

    for _, row in holdings.iterrows():
        ticker = row["ticker"]
        ind = signals.compute_indicators(ticker, end_date=target)
        if ind is None:
            warnings.append({
                "ticker": ticker,
                "name": _get_name(ticker, ticker_info),
                "should_exit": False,
                "reason": "데이터 부족",
                "pnl_pct": float(row.get("eval_pl_pct", 0)),
            })
            continue

        # 보유일 추정 (DB에 매수일 없으므로 N/A)
        hold_days = 0

        exit_result = signals.check_exit(
            ticker=ticker,
            avg_price=float(row["avg_price"]),
            hold_days=hold_days,
            ind=ind,
            rules=rules,
        )
        if exit_result["should_exit"] or exit_result["pnl_pct"] <= rules["exit_signal"]["stop_loss_pct"] + 2:
            warnings.append({
                "ticker": ticker,
                "name": _get_name(ticker, ticker_info),
                "current_price": ind["close"],
                "avg_price": float(row["avg_price"]),
                "pnl_pct": exit_result["pnl_pct"],
                "should_exit": exit_result["should_exit"],
                "reason": exit_result["reason"],
                "indicators": {k: v for k, v in ind.items() if k != "ticker"},
            })

    # ── 4. 진입 후보 탐색 (candidates) ─────────────────────────────────────
    candidates: list[dict] = []

    if halted:
        log.info("신규 진입 차단 — candidates 생성 건너뜀")
    elif portfolio_status["position_count"] >= rules["position"]["max_positions"]:
        log.info("최대 보유 종목 수 도달 — candidates 생성 건너뜀")
    else:
        filtered = universe.filter_universe(ticker_info)
        # 이미 보유 중인 종목 제외
        filtered = filtered[~filtered["ticker"].isin(held_tickers)]

        log.info(f"유니버스 필터 후 후보 풀: {len(filtered)}종목")

        # 전체 지표를 2번의 쿼리로 일괄 계산
        filtered_tickers = filtered["ticker"].tolist()
        all_indicators = signals.compute_indicators_batch(filtered_tickers, end_date=target)
        ticker_row = {row["ticker"]: row for _, row in filtered.iterrows()}

        sl_pct = abs(rules["exit_signal"]["stop_loss_pct"]) / 100
        tp_pct = rules["exit_signal"]["take_profit_pct"] / 100

        for ticker, ind in all_indicators.items():
            if ind is None:
                continue

            entry_result = signals.check_entry(ind, rules)
            if not entry_result["passed"]:
                continue

            row = ticker_row[ticker]
            entry_guide = {
                "entry_price": ind["close"],
                "stop_loss_price": round(ind["close"] * (1 - sl_pct)),
                "take_profit_price": round(ind["close"] * (1 + tp_pct)),
            }

            candidates.append({
                "ticker": ticker,
                "name": _get_name(ticker, ticker_info),
                "market": row.get("market"),
                "sector": row.get("sector"),
                "market_cap_billion": _cap_billion(row.get("market_cap")),
                "indicators": {k: v for k, v in ind.items() if k != "ticker"},
                "entry_checks": entry_result["checks"],
                "entry_guide": entry_guide,
            })

        # 외국인 순매수 기준 상위 정렬
        candidates.sort(key=lambda x: x["indicators"].get("foreign_net_5d", 0), reverse=True)
        candidates = candidates[:10]  # 최대 10개

    return {
        "candidates": candidates,
        "warnings": warnings,
        "portfolio_status": portfolio_status,
        "run_date": target.isoformat(),
        "halted": halted,
    }


def _get_name(ticker: str, ticker_info: pd.DataFrame) -> str:
    if ticker_info.empty:
        return ticker
    row = ticker_info[ticker_info["ticker"] == ticker]
    return row["name"].iloc[0] if not row.empty else ticker


def _cap_billion(market_cap) -> float | None:
    if market_cap is None or pd.isna(market_cap):
        return None
    return round(market_cap / 1_0000_0000, 0)
