"""
일요일 19:00 자동 실행 — 주간 리포트 생성.

실행:
    uv run python scripts/weekly_report.py
    uv run python scripts/weekly_report.py --cash 1000000
    uv run python scripts/weekly_report.py --date 2026-05-18 --cash 500000
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.report.weekly import generate
from src.utils.logging import get_logger

log = get_logger("weekly_report")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="주간 리포트 생성")
    parser.add_argument("--date", type=str, help="기준일 YYYY-MM-DD (기본: 오늘)")
    parser.add_argument("--cash", type=float, default=0.0, help="현금 잔고 (원)")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else None

    log.info("=== 주간 리포트 생성 시작 ===")
    path = generate(report_date=report_date, cash=args.cash)
    log.info(f"=== 완료: {path} ===")
    print(f"\n리포트 위치: {path}")
