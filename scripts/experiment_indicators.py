#!/usr/bin/env python3
"""Phase 12-4: 진입 조건 개선 후보 비교 실험.

베이스라인 대비 3가지 후보를 동일 기간·동일 유니버스로 비교한다.

시나리오:
  A. 베이스라인  — 현행 rules.yaml 그대로
  B. RSI_48     — RSI 상단 55 → 48
  C. MA20_기울기 — MA20 기울기 양수 필수 조건 추가
  D. 복합        — B + C + 거래량비율 상한 5.0
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.runner import run_backtest
from src.data import storage

SCENARIOS = [
    {
        "name": "A. 베이스라인",
        "params": {},
    },
    {
        "name": "B. RSI_48",
        "params": {"rsi_hi_override": 48},
    },
    {
        "name": "C. MA20_기울기",
        "params": {"ma20_slope_filter": True},
    },
    {
        "name": "D. 복합(RSI48+MA20기울기+거래량상한)",
        "params": {"rsi_hi_override": 48, "ma20_slope_filter": True, "vol_ratio_max": 5.0},
    },
]


def _summarize(result: dict) -> dict:
    log = result.get("trade_log", [])
    total = len(log)
    losing = [t for t in log if t["pnl_pct"] < 0]
    avg_loss = sum(t["pnl_pct"] for t in losing) / len(losing) if losing else 0
    return {
        "수익률": f"{result['total_return_pct']:+.2f}%",
        "MDD": f"{result['avg_mdd_pct']:.1f}%",
        "거래수": total,
        "승률": f"{result['win_rate']:.1f}%",
        "손실건": len(losing),
        "평균손실": f"{avg_loss:+.2f}%",
    }


def _print_comparison(summaries: list[tuple[str, dict]]) -> None:
    keys = list(summaries[0][1].keys())
    name_w = max(len(s[0]) for s in summaries) + 2
    col_w = 12

    header = f"{'시나리오':<{name_w}}" + "".join(f"{k:>{col_w}}" for k in keys)
    print(header)
    print("─" * len(header))
    for name, summary in summaries:
        row = f"{name:<{name_w}}" + "".join(f"{summary[k]:>{col_w}}" for k in keys)
        print(row)


def main():
    parser = argparse.ArgumentParser(description="진입 조건 개선 후보 비교 실험")
    parser.add_argument("--start", default="2025-11-24")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--capital", type=float, default=5_000_000)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", default="docs/phase12-indicator-experiment.json")
    args = parser.parse_args()

    tickers = storage.get_top_trading_value_tickers(limit=args.limit, end=args.end)
    if not tickers:
        print("유니버스 조회 실패")
        return

    print(f"기간: {args.start} ~ {args.end}  유니버스: {len(tickers)}종목\n")

    results = []
    for sc in SCENARIOS:
        print(f"[{sc['name']}] 실행 중...", end=" ", flush=True)
        r = run_backtest(tickers, args.start, args.end, args.capital, sc["params"])
        summary = _summarize(r)
        results.append((sc["name"], summary, r))
        print(f"완료 (거래 {summary['거래수']}건, 승률 {summary['승률']})")

    print("\n" + "=" * 70)
    print("비교 결과")
    print("=" * 70)
    _print_comparison([(name, s) for name, s, _ in results])
    print()

    # 개선 분석
    base_wr = float(results[0][1]["승률"].rstrip("%"))
    base_ret = float(results[0][1]["수익률"].rstrip("%"))
    base_mdd = float(results[0][1]["MDD"].rstrip("%"))

    print("베이스라인 대비 변화:")
    for name, summary, _ in results[1:]:
        wr = float(summary["승률"].rstrip("%"))
        ret = float(summary["수익률"].rstrip("%"))
        mdd = float(summary["MDD"].rstrip("%"))
        trades = summary["거래수"]
        print(
            f"  {name}: 수익률 {ret-base_ret:+.2f}%p  "
            f"MDD {mdd-base_mdd:+.1f}%p  "
            f"승률 {wr-base_wr:+.1f}%p  "
            f"거래수 {trades}건"
        )

    # 베이스라인: 승/패 거래 지표 분포 비교
    base_log = results[0][2].get("trade_log", [])
    winning_log = [t for t in base_log if t["pnl_pct"] >= 0]
    losing_log  = [t for t in base_log if t["pnl_pct"] < 0]

    def _avg(lst, key):
        return sum(t[key] for t in lst) / len(lst) if lst else 0

    def _pct_above(lst, key, threshold):
        return sum(1 for t in lst if t[key] > threshold) / len(lst) * 100 if lst else 0

    print("\n[베이스라인 승/패 거래 지표 비교]")
    print(f"{'지표':<20} {'수익 거래':>12} {'손실 거래':>12}")
    print("-" * 46)
    metrics = [
        ("RSI 평균", "rsi", None),
        ("MA20 기울기 평균", "ma20_slope", None),
        ("거래량비율 평균", "vol_ratio", None),
    ]
    for label, key, _ in metrics:
        w = _avg(winning_log, key)
        l = _avg(losing_log, key)
        print(f"{label:<20} {w:>12.2f} {l:>12.2f}")

    print(f"{'RSI > 50 비율':<20} {_pct_above(winning_log, 'rsi', 50):>11.0f}% {_pct_above(losing_log, 'rsi', 50):>11.0f}%")
    print(f"{'MA20 기울기 음수':.<20} {_pct_above(winning_log, 'ma20_slope', 0):>11.0f}% (양수)  {sum(1 for t in losing_log if t['ma20_slope']<0)/len(losing_log)*100 if losing_log else 0:>9.0f}% (음수)")
    print(f"{'거래수':<20} {len(winning_log):>12} {len(losing_log):>12}")

    # JSON 저장
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    export = {
        "generated_at": date.today().isoformat(),
        "period": f"{args.start} ~ {args.end}",
        "universe": len(tickers),
        "scenarios": [
            {
                "name": name,
                "params": SCENARIOS[i]["params"],
                "summary": summary,
            }
            for i, (name, summary, _) in enumerate(results)
        ],
    }
    out.write_text(json.dumps(export, ensure_ascii=False, indent=2))
    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
