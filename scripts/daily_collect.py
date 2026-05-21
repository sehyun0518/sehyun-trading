"""
매일 16:00 실행 — 일봉·재무·수급 수집 + 잔고 동기화.

실행:
    uv run python scripts/daily_collect.py
    uv run python scripts/daily_collect.py --date 2026-05-16   # 특정 날짜 재수집
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# pykrx 임포트 전 .env 로드 필수 (KRX_ID / KRX_PW)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import pandas as pd

from src.data import kis_client, pykrx_collector, storage
from src.utils.dates import get_last_trading_day, is_trading_day
from src.utils.logging import get_logger

log = get_logger("daily_collect")
log.info(f"운영 모드: {kis_client.get_mode().upper()} ({'모의투자' if kis_client.get_mode() == 'paper' else '실전투자'})")


def collect_ohlcv(target: date) -> None:
    log.info(f"OHLCV 수집 시작: {target}")
    df = pykrx_collector.collect_universe_ohlcv(target)
    if df.empty:
        log.warning("OHLCV 데이터 없음 (비거래일 또는 pykrx 오류)")
        return
    n = storage.upsert_ohlcv(df)
    log.info(f"OHLCV upsert: {n}건")


def collect_fundamentals(target: date) -> None:
    log.info(f"재무지표 수집 시작: {target}")
    df = pykrx_collector.collect_fundamentals(target)
    if df.empty:
        log.warning("재무지표 데이터 없음")
        return
    n = storage.upsert_fundamentals(df)
    log.info(f"재무지표 upsert: {n}건")


def collect_trading_flow(target: date) -> None:
    """보유 종목 + 유니버스 상위 종목 수급 수집 (KIS API 기반)."""
    log.info("수급 수집 시작")
    universe = storage.get_universe()
    if universe.empty:
        log.warning("종목 유니버스 없음 — ticker_info 먼저 수집 필요")
        return

    holdings = storage.get_holdings()
    held_tickers = set(holdings["ticker"].tolist()) if not holdings.empty else set()
    top_tickers = (
        universe.dropna(subset=["market_cap"])
        .nlargest(100, "market_cap")["ticker"]
        .tolist()
    )
    target_tickers = list(held_tickers | set(top_tickers))

    success = fail = 0
    for ticker in target_tickers:
        try:
            rows = kis_client.get_investor_trading(ticker)
            if rows:
                df = pd.DataFrame(rows)
                storage.upsert_trading_flow(df)
                success += 1
            else:
                fail += 1  # ETF·우선주 등 데이터 미제공 종목
        except Exception as e:
            log.warning(f"수급 수집 오류 {ticker}: {e}")
            fail += 1

    log.info(f"수급 upsert: 성공 {success}건, 데이터없음 {fail}건")


def collect_ticker_info() -> None:
    log.info("종목 정보 수집 시작")
    df = pykrx_collector.collect_ticker_info()
    if df.empty:
        log.warning("종목 정보 없음")
        return
    n = storage.upsert_ticker_info(df)
    log.info(f"종목 정보 upsert: {n}건")


def sync_holdings() -> None:
    log.info("잔고 동기화 시작")
    try:
        items = kis_client.get_holdings()
        if not items:
            log.info("보유 종목 없음")
            return
        df = pd.DataFrame(items)
        n = storage.upsert_holdings(df)
        log.info(f"잔고 upsert: {n}건")
    except Exception as e:
        log.error(f"잔고 동기화 실패: {e}")


def run(target: date, force: bool = False) -> None:
    log.info(f"=== 일일 수집 시작: {target} ===")

    if not force and not is_trading_day(target):
        log.info(f"{target}은 비거래일 — 수집 건너뜀 (--force 로 강제 실행 가능)")
        return

    # 1. 종목 정보 (월요일 또는 강제 실행 시)
    if target.weekday() == 0 or force:
        collect_ticker_info()

    # 2. OHLCV
    collect_ohlcv(target)

    # 3. 재무지표
    collect_fundamentals(target)

    # 4. 수급
    collect_trading_flow(target)

    # 5. 잔고 동기화
    sync_holdings()

    # 6. 규칙 엔진 실행 → 캐시 저장 (API가 캐시에서 즉시 응답하도록)
    try:
        from src.rules.engine import run as run_engine
        engine_result = run_engine(target_date=target)
        storage.save_engine_cache(engine_result)
        log.info(f"엔진 캐시 저장: 후보 {len(engine_result['candidates'])}종목, 경고 {len(engine_result['warnings'])}건")
    except Exception as e:
        log.error(f"엔진 캐시 저장 실패: {e}")

    log.info(f"=== 일일 수집 완료: {target} ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="일일 데이터 수집")
    parser.add_argument("--date", type=str, help="수집 날짜 YYYY-MM-DD (기본: 마지막 거래일)")
    parser.add_argument("--force", action="store_true", help="비거래일에도 강제 실행")
    args = parser.parse_args()

    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = get_last_trading_day()

    run(target_date, force=args.force)
