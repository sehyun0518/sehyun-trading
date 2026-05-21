"""기술적 지표 계산 및 진입·청산 시그널 판정."""
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import pandas_ta as ta
import yaml

from src.data import storage


def _load_rules() -> dict:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "rules.yaml") as f:
        return yaml.safe_load(f)


def compute_indicators(ticker: str, end_date: date | None = None) -> dict | None:
    """
    단일 종목의 기술적 지표 계산.
    반환: {ticker, close, ma20, ma60, rsi, volume_ratio_5d, foreign_net_5d, ...}
    None이면 데이터 부족.
    """
    end = end_date or date.today()
    start = end - timedelta(days=200)  # 지표 계산용 충분한 히스토리

    ohlcv = storage.get_ohlcv(ticker, start.isoformat(), end.isoformat())
    if len(ohlcv) < 60:
        return None

    ohlcv = ohlcv.sort_values("date").reset_index(drop=True)
    close = ohlcv["close"]
    volume = ohlcv["volume"]

    ma20 = ta.sma(close, length=20).iloc[-1]
    ma60 = ta.sma(close, length=60).iloc[-1]
    rsi = ta.rsi(close, length=14).iloc[-1]

    vol_5d_avg = volume.iloc[-6:-1].mean()  # 직전 5일 평균 (오늘 제외)
    vol_today = volume.iloc[-1]
    volume_ratio = vol_today / vol_5d_avg if vol_5d_avg > 0 else 0.0

    # 수급: 최근 5거래일 외국인 순매수 합산
    flow = storage.get_trading_flow(ticker, days=5)
    foreign_net_5d = float(flow["foreign_net"].sum()) if not flow.empty else 0.0

    latest_close = float(close.iloc[-1])
    return {
        "ticker": ticker,
        "close": latest_close,
        "ma20": float(ma20) if pd.notna(ma20) else None,
        "ma60": float(ma60) if pd.notna(ma60) else None,
        "rsi": float(rsi) if pd.notna(rsi) else None,
        "volume_ratio_5d": round(volume_ratio, 3),
        "foreign_net_5d": foreign_net_5d,
    }


def check_entry(ind: dict, rules: dict | None = None) -> dict:
    """
    진입 조건 AND 검사.
    반환: {passed: bool, checks: {조건명: bool}}
    """
    if rules is None:
        rules = _load_rules()
    e = rules["entry_signal"]
    checks = {}

    # 종가 > N일 이평선
    ma_len = e.get("close_above_ma", 20)
    ma_key = f"ma{ma_len}"
    ma_val = ind.get(ma_key)
    checks[f"close_above_ma{ma_len}"] = (
        ma_val is not None and ind["close"] > ma_val
    )

    # RSI 범위
    rsi_lo, rsi_hi = e.get("rsi_range", [30, 55])
    rsi = ind.get("rsi")
    checks["rsi_in_range"] = rsi is not None and rsi_lo <= rsi <= rsi_hi

    # 외국인 순매수 양수
    if e.get("foreign_net_5d_positive", False):
        checks["foreign_net_positive"] = ind.get("foreign_net_5d", 0) > 0

    # 거래량 비율
    vol_min = e.get("volume_ratio_5d", 1.0)
    checks["volume_ratio_ok"] = ind.get("volume_ratio_5d", 0) >= vol_min

    checks = {k: bool(v) for k, v in checks.items()}
    passed = all(checks.values())
    return {"passed": passed, "checks": checks}


def check_exit(ticker: str, avg_price: float, hold_days: int,
               ind: dict, rules: dict | None = None) -> dict:
    """
    청산 조건 OR 검사.
    반환: {should_exit: bool, reason: str | None, checks: {조건명: bool}}
    """
    if rules is None:
        rules = _load_rules()
    ex = rules["exit_signal"]
    checks = {}
    triggered = []

    close = ind.get("close", 0)
    if avg_price > 0:
        pnl_pct = (close - avg_price) / avg_price * 100
    else:
        pnl_pct = 0.0

    # 익절
    tp = ex.get("take_profit_pct", 15)
    checks["take_profit"] = pnl_pct >= tp
    if checks["take_profit"]:
        triggered.append(f"익절 ({pnl_pct:.1f}% ≥ {tp}%)")

    # 손절
    sl = ex.get("stop_loss_pct", -7)
    checks["stop_loss"] = pnl_pct <= sl
    if checks["stop_loss"]:
        triggered.append(f"손절 ({pnl_pct:.1f}% ≤ {sl}%)")

    # 시간 청산
    ts = ex.get("time_stop_days", 60)
    checks["time_stop"] = hold_days >= ts
    if checks["time_stop"]:
        triggered.append(f"보유기간 ({hold_days}일 ≥ {ts}일)")

    # MA 이탈
    ma_break_len = ex.get("ma_break", 60)
    ma_key = f"ma{ma_break_len}"
    ma_val = ind.get(ma_key)
    if ma_val is not None:
        checks["ma_break"] = close < ma_val
        if checks["ma_break"]:
            triggered.append(f"MA{ma_break_len} 하향이탈")

    checks = {k: bool(v) for k, v in checks.items()}
    should_exit = any(checks.values())
    return {
        "should_exit": should_exit,
        "reason": " / ".join(triggered) if triggered else None,
        "pnl_pct": round(pnl_pct, 2),
        "checks": checks,
    }
