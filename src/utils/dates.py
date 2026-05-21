"""한국 거래일 처리 유틸리티."""
from datetime import date, timedelta

from pykrx import stock


def get_last_trading_day(reference: date | None = None) -> date:
    """기준일 이전 마지막 거래일 반환. 기본값: 오늘."""
    ref = reference or date.today()
    # 최근 30일 내 거래일 목록에서 기준일 이전 마지막 날 탐색
    start = (ref - timedelta(days=30)).strftime("%Y%m%d")
    end = ref.strftime("%Y%m%d")
    trading_days = stock.get_previous_business_days(fromdate=start, todate=end)
    if not trading_days:
        raise RuntimeError("거래일 조회 실패")
    last = trading_days[-1]
    return date(last.year, last.month, last.day)


def is_trading_day(d: date | None = None) -> bool:
    target = d or date.today()
    last = get_last_trading_day(target)
    return last == target
