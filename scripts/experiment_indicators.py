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
from src.data.pykrx_collector import get_market_ma20_valid_dates


def _fetch_market_dates(start: str, end: str) -> tuple[frozenset | None, frozenset | None]:
    """KOSPI(1001), KOSDAQ(2001) 각각의 MA20 유효 날짜 집합."""
    results = []
    for label, ticker in [("KOSPI", "1001"), ("KOSDAQ", "2001")]:
        print(f"{label} MA20 날짜 조회 중...", end=" ", flush=True)
        try:
            dates = get_market_ma20_valid_dates(start, end, ticker)
            print(f"{len(dates)}일")
            results.append(dates)
        except Exception as e:
            print(f"실패 ({e})")
            results.append(None)
    return results[0], results[1]


def _build_scenarios(start: str, end: str, tickers: list[str]) -> list[dict]:
    kospi_dates, kosdaq_dates = _fetch_market_dates(start, end)

    scenarios = [
        {"name": "A. 베이스라인",                      "params": {}, "tickers": tickers},
        {"name": "B. RSI_48",                          "params": {"rsi_hi_override": 48}, "tickers": tickers},
        {"name": "C. MA20_기울기",                     "params": {"ma20_slope_filter": True}, "tickers": tickers},
        {"name": "D. 복합(RSI48+MA20기울기+거래량상한)", "params": {"rsi_hi_override": 48, "ma20_slope_filter": True, "vol_ratio_max": 5.0}, "tickers": tickers},
    ]
    if kospi_dates:
        scenarios.append({
            "name": "E. KOSPI_MA20_필터",
            "params": {"market_valid_dates": kospi_dates},
            "tickers": tickers,
        })
    if kospi_dates and kosdaq_dates:
        # 시나리오 F: 종목의 상장 시장에 맞는 지수 필터 적용
        ticker_market = _load_ticker_market(tickers)
        kospi_tickers = [t for t in tickers if ticker_market.get(t) == "KOSPI"]
        kosdaq_tickers = [t for t in tickers if ticker_market.get(t) == "KOSDAQ"]
        if kospi_tickers or kosdaq_tickers:
            scenarios.append({
                "name": "F. 상장시장별_지수_필터",
                "params": None,  # 특수 처리 — 아래서 split 실행
                "tickers": tickers,
                "_split": {
                    "KOSPI": {"tickers": kospi_tickers, "params": {"market_valid_dates": kospi_dates}},
                    "KOSDAQ": {"tickers": kosdaq_tickers, "params": {"market_valid_dates": kosdaq_dates}},
                },
            })
    return scenarios


def _load_ticker_market(tickers: list[str]) -> dict[str, str]:
    """DB ticker_info에서 상장 시장 조회."""
    df = storage._read("SELECT ticker, market FROM ticker_info WHERE market IS NOT NULL")
    if df.empty:
        return {}
    return dict(zip(df["ticker"], df["market"]))


def _merge_results(per_ticker: list[dict], trade_log: list[dict], capital: float, start: str, end: str) -> dict:
    """분리 실행된 결과를 하나로 합산."""
    if not per_ticker:
        return {"trade_log": [], "total_return_pct": 0, "avg_mdd_pct": 0, "win_rate": 0, "per_ticker": []}
    total_trades = sum(r["trades"] for r in per_ticker)
    total_won = sum(r["won"] for r in per_ticker)
    avg_return = sum(r["return_pct"] for r in per_ticker) / len(per_ticker)
    avg_mdd = sum(r["mdd_pct"] for r in per_ticker) / len(per_ticker)
    return {
        "start": start, "end": end, "capital": capital,
        "total_return_pct": round(avg_return, 2),
        "avg_mdd_pct": round(avg_mdd, 2),
        "trades": total_trades,
        "win_rate": round(total_won / total_trades * 100 if total_trades else 0, 1),
        "per_ticker": sorted(per_ticker, key=lambda x: x["return_pct"], reverse=True),
        "trade_log": trade_log,
    }


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

    SCENARIOS = _build_scenarios(args.start, args.end, tickers)

    results = []
    for sc in SCENARIOS:
        print(f"[{sc['name']}] 실행 중...", end=" ", flush=True)
        if sc.get("_split"):
            # 시나리오 F: 상장 시장별 분리 실행 후 합산
            combined_log = []
            combined_per_ticker = []
            for mkt, cfg in sc["_split"].items():
                if not cfg["tickers"]:
                    continue
                r = run_backtest(cfg["tickers"], args.start, args.end, args.capital, cfg["params"])
                combined_log.extend(r.get("trade_log", []))
                combined_per_ticker.extend(r.get("per_ticker", []))
            # 합산 결과 구성
            r = _merge_results(combined_per_ticker, combined_log, args.capital, args.start, args.end)
        else:
            r = run_backtest(sc["tickers"], args.start, args.end, args.capital, sc["params"])
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
                "params": {
                    k: v
                    for k, v in (SCENARIOS[i].get("params") or {}).items()
                    if k not in {"market_valid_dates"}
                },
                "summary": summary,
            }
            for i, (name, summary, _) in enumerate(results)
        ],
    }
    out.write_text(json.dumps(export, ensure_ascii=False, indent=2))
    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
