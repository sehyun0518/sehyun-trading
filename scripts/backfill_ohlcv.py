"""
과거 OHLCV 일괄 수집 (최초 1회 실행).
pykrx get_market_ohlcv_by_ticker 를 날짜 반복으로 수집.

실행:
    uv run python scripts/backfill_ohlcv.py                    # 기본 1년
    uv run python scripts/backfill_ohlcv.py --start 2023-01-01 --end 2026-05-17
"""
import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# pykrx 임포트 전 .env 로드 (KRX_ID / KRX_PW 필요)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from pykrx import stock

from src.data import storage
from src.utils.logging import get_logger

log = get_logger("backfill_ohlcv")


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def is_trading_day_fast(d: date) -> bool:
    return d.weekday() < 5  # 주말 제외 (공휴일은 pykrx가 빈 DF 반환)


def backfill(start: date, end: date) -> None:
    log.info(f"OHLCV 백필 시작: {start} ~ {end}")
    total_rows = 0
    skipped = 0

    for d in daterange(start, end):
        if not is_trading_day_fast(d):
            continue

        d_str = d.strftime("%Y%m%d")
        date_iso = d.isoformat()

        # 이미 수집된 날짜 스킵
        existing = storage.get_ohlcv_multi(["005930"], date_iso, date_iso)
        if not existing.empty:
            skipped += 1
            continue

        rows_day = 0
        for market in ("KOSPI", "KOSDAQ"):
            try:
                df = stock.get_market_ohlcv_by_ticker(d_str, market=market)
                if df is None or df.empty:
                    continue
                df = df.reset_index()
                df = df.rename(columns={
                    "티커": "ticker",
                    "시가": "open", "고가": "high", "저가": "low", "종가": "close",
                    "거래량": "volume", "거래대금": "value",
                })
                df["date"] = date_iso
                keep = ["ticker", "date", "open", "high", "low", "close", "volume", "value"]
                df = df[[c for c in keep if c in df.columns]]
                n = storage.upsert_ohlcv(df)
                rows_day += n
            except Exception as e:
                log.warning(f"{d} {market} 수집 실패: {e}")

        total_rows += rows_day
        if rows_day > 0:
            log.info(f"{d}: {rows_day}건")
        time.sleep(0.3)  # pykrx rate limit

    log.info(f"백필 완료: 총 {total_rows}건 저장, {skipped}일 스킵")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=(date.today() - timedelta(days=365)).isoformat())
    parser.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    args = parser.parse_args()

    backfill(date.fromisoformat(args.start), date.fromisoformat(args.end))
