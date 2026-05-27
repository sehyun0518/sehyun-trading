#!/usr/bin/env python3
"""Phase 12-3: 백테스트 손실 거래 실패 원인 분류.

분류 기준 (복수 해당 가능):
  추세_역행    — 진입 시 MA20 기울기(5일) 음수
  거래량_착시  — 진입일 거래량비율 > 3.0 (비정상 폭등, 지속성 낮음)
  RSI_경계_진입 — 진입 RSI > 50 (유효 범위 상단, 추가 상승 여력 제한)
  손절_지연    — 청산 사유: time_stop (60일 보유 후에도 SL/TP 미도달, 결국 손실)
  MA60_즉시_이탈 — 청산 사유: ma_break이고 보유 기간 < 10일
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.runner import run_backtest
from src.data import storage


_CATEGORIES = {
    "추세_역행":    lambda t: t["ma20_slope"] < 0,
    "거래량_착시":  lambda t: t["vol_ratio"] > 3.0,
    "RSI_경계_진입": lambda t: t["rsi"] > 50,
    "손절_지연":    lambda t: t["exit_reason"] == "time_stop",
    "MA60_즉시_이탈": lambda t: t["exit_reason"] == "ma_break" and t["bars_held"] < 10,
}


def classify(trade: dict) -> list[str]:
    matched = [name for name, fn in _CATEGORIES.items() if fn(trade)]
    return matched or ["분류_불가"]


def _print_table(rows: list[dict], cols: list[tuple]) -> None:
    """cols: [(header, key, width), ...]"""
    fmt_h = "  ".join(f"{{:<{w}}}" for _, _, w in cols)
    fmt_r = "  ".join(f"{{:<{w}}}" for _, _, w in cols)
    print(fmt_h.format(*[h for h, _, _ in cols]))
    print("-" * (sum(w for _, _, w in cols) + 2 * (len(cols) - 1)))
    for r in rows:
        print(fmt_r.format(*[str(r.get(k, ""))[:w] for _, k, w in cols]))


def main():
    parser = argparse.ArgumentParser(description="백테스트 손실 거래 실패 원인 분류")
    parser.add_argument("--start", default="2025-11-24", help="백테스트 시작일")
    parser.add_argument("--end", default=date.today().isoformat(), help="백테스트 종료일")
    parser.add_argument("--capital", type=float, default=5_000_000)
    parser.add_argument("--limit", type=int, default=100, help="유니버스 종목 수")
    parser.add_argument("--out", default="docs/phase12-failure-analysis.json")
    args = parser.parse_args()

    # 유니버스
    tickers = storage.get_top_trading_value_tickers(limit=args.limit, end=args.end)
    if not tickers:
        print("유니버스 조회 실패: daily_ohlcv 데이터 없음")
        return

    print(f"백테스트 실행: {args.start} ~ {args.end}, {len(tickers)}종목")
    result = run_backtest(tickers, args.start, args.end, args.capital)

    trade_log = result.get("trade_log", [])
    if not trade_log:
        print("거래 기록 없음 (진입 조건 미충족 또는 데이터 부족)")
        return

    winning = [t for t in trade_log if t["pnl_pct"] >= 0]
    losing = [t for t in trade_log if t["pnl_pct"] < 0]

    print(f"\n총 거래: {len(trade_log)}건  |  수익: {len(winning)}건  |  손실: {len(losing)}건")
    if not losing:
        print("손실 거래 없음")
        return

    # ── 실패 원인 분류 ──────────────────────────────────────────────────────
    category_count: dict[str, int] = defaultdict(int)
    category_pnl: dict[str, list[float]] = defaultdict(list)
    for t in losing:
        for c in classify(t):
            category_count[c] += 1
            category_pnl[c].append(t["pnl_pct"])

    print("\n[실패 원인 분류]")
    print(f"{'분류':<15}  {'건수':>4}  {'비율':>6}  {'평균손실':>8}")
    print("-" * 40)
    for cat, cnt in sorted(category_count.items(), key=lambda x: -x[1]):
        pct = cnt / len(losing) * 100
        avg_pnl = sum(category_pnl[cat]) / len(category_pnl[cat])
        print(f"{cat:<15}  {cnt:>4}  {pct:>5.1f}%  {avg_pnl:>+7.2f}%")

    # ── 청산 사유별 요약 ────────────────────────────────────────────────────
    reason_count: dict[str, int] = defaultdict(int)
    for t in losing:
        reason_count[t["exit_reason"]] += 1

    print("\n[청산 사유별 손실 건수]")
    for reason, cnt in sorted(reason_count.items(), key=lambda x: -x[1]):
        print(f"  {reason:<15}: {cnt}건")

    # ── 손실 상위 15건 ──────────────────────────────────────────────────────
    worst = sorted(losing, key=lambda x: x["pnl_pct"])[:15]
    print("\n[손실 상위 15건]")
    for t in worst:
        cats = ", ".join(classify(t))
        print(
            f"  {t['ticker']}  {t['entry_date']}→{t['exit_date']}"
            f"  {t['pnl_pct']:>+6.1f}%  ({t['exit_reason']}, {t['bars_held']}일)"
            f"  [{cats}]"
        )

    # ── RSI/MA 분포 요약 ────────────────────────────────────────────────────
    avg_rsi = sum(t["rsi"] for t in losing) / len(losing)
    avg_slope = sum(t["ma20_slope"] for t in losing) / len(losing)
    avg_volr = sum(t["vol_ratio"] for t in losing) / len(losing)
    pct_neg_slope = sum(1 for t in losing if t["ma20_slope"] < 0) / len(losing) * 100
    print(f"\n[손실 거래 진입 지표 평균]")
    print(f"  RSI 평균: {avg_rsi:.1f}  (50 초과 비율: {sum(1 for t in losing if t['rsi']>50)/len(losing)*100:.0f}%)")
    print(f"  MA20 기울기 평균: {avg_slope:+.2f}  (음수 비율: {pct_neg_slope:.0f}%)")
    print(f"  거래량비율 평균: {avg_volr:.2f}")

    # ── JSON 저장 ───────────────────────────────────────────────────────────
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    report = {
        "generated_at": date.today().isoformat(),
        "period": f"{args.start} ~ {args.end}",
        "universe": len(tickers),
        "total_trades": len(trade_log),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "category_count": dict(category_count),
        "exit_reason_count": dict(reason_count),
        "avg_entry_rsi": round(avg_rsi, 1),
        "avg_ma20_slope": round(avg_slope, 2),
        "avg_vol_ratio": round(avg_volr, 2),
        "worst_trades": worst,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
