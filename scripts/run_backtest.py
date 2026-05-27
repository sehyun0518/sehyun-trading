"""
백테스트 실행 스크립트.

실행:
    uv run python scripts/run_backtest.py
    uv run python scripts/run_backtest.py --start 2025-05-01 --end 2026-05-17 --capital 5000000
    uv run python scripts/run_backtest.py --tickers 005930 000660 035420
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.runner import run_backtest
from src.data import storage
from src.rules.universe import filter_universe
from src.utils.logging import get_logger

log = get_logger("run_backtest")


def main():
    parser = argparse.ArgumentParser(description="백테스트 실행")
    parser.add_argument("--start", default="2025-05-01")
    parser.add_argument("--end", default="2026-05-17")
    parser.add_argument("--capital", type=float, default=5_000_000)
    parser.add_argument(
        "--tickers", nargs="+",
        help="특정 티커 지정 (미지정 시 유니버스 시총 상위 100)"
    )
    args = parser.parse_args()

    # 티커 결정
    if args.tickers:
        tickers = args.tickers
    else:
        info = storage.get_universe()
        filtered = filter_universe(info)
        tickers = (
            filtered.dropna(subset=["market_cap"])
            .nlargest(100, "market_cap")["ticker"]
            .tolist()
        )
        if len(tickers) < 20:
            log.warning(
                "market_cap 유니버스가 %s개뿐입니다. 최신 거래대금 상위 100개로 대체합니다.",
                len(tickers),
            )
            tickers = storage.get_top_trading_value_tickers(limit=100, end=args.end)

    log.info(f"백테스트: {args.start}~{args.end}, 자본금 {args.capital:,.0f}원, 종목 {len(tickers)}개")

    result = run_backtest(
        tickers=tickers,
        start=args.start,
        end=args.end,
        capital=args.capital,
    )

    print("\n" + "=" * 50)
    print("백테스트 결과")
    print("=" * 50)
    print(f"기간        : {result['start']} ~ {result['end']}")
    print(f"초기 자본금 : {result['capital']:>15,.0f}원")
    print(f"최종 평가금 : {result['final_value']:>15,.0f}원")
    print(f"수익률      : {result['total_return_pct']:>+.2f}%")
    print(f"평균 MDD    : {result['avg_mdd_pct']:.2f}%")
    print(f"거래 횟수   : {result['trades']}회 (종목당 {result['trades']//max(result['tickers_loaded'],1):.1f}회)")
    print(f"승률        : {result['win_rate']:.1f}%")
    if result["sharpe"] is not None:
        print(f"샤프 비율   : {result['sharpe']:.3f}")
    print(f"요청 종목   : {result['tickers_requested']}개")
    print(f"데이터 종목 : {result['tickers_loaded']}개")
    print(f"스킵 종목   : {result['tickers_skipped']}개")
    print("=" * 50)

    top = result["per_ticker"][:5]
    bot = result["per_ticker"][-5:]
    if top:
        print("\n수익률 상위 5종목:")
        for r in top:
            print(f"  {r['ticker']}: {r['return_pct']:>+.1f}% ({r['trades']}거래)")
    if bot:
        print("\n수익률 하위 5종목:")
        for r in bot:
            print(f"  {r['ticker']}: {r['return_pct']:>+.1f}% ({r['trades']}거래)")
    if result.get("skipped"):
        print("\n스킵 예시:")
        for r in result["skipped"][:5]:
            print(f"  {r['ticker']}: {r['reason']}")
    print()


if __name__ == "__main__":
    main()
