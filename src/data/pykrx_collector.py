"""pykrx 기반 데이터 수집기. pykrx 1.2.x — KRX 로그인 필요 (KRX_ID / KRX_PW 환경변수)."""
import time
from datetime import date

import pandas as pd
from pykrx import stock

_RETRY = 3
_DELAY = 5


def _retry(fn, *args, **kwargs):
    for attempt in range(_RETRY):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == _RETRY - 1:
                raise
            time.sleep(_DELAY)


def _date_str(d: date | str) -> str:
    return d.strftime("%Y%m%d") if isinstance(d, date) else d.replace("-", "")


def _iso(d: str) -> str:
    """YYYYMMDD → YYYY-MM-DD"""
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


# ── 유니버스 OHLCV ────────────────────────────────────────────────────────────

def collect_universe_ohlcv(target_date: date | str) -> pd.DataFrame:
    """KOSPI + KOSDAQ 전 종목 일봉. 컬럼: ticker, date, open, high, low, close, volume, value."""
    d = _date_str(target_date)
    date_iso = _iso(d)
    frames = []
    for market in ("KOSPI", "KOSDAQ"):
        # pykrx 1.2.x: 날짜 단일 기준 전 종목 조회
        df = _retry(stock.get_market_ohlcv_by_ticker, d, market=market)
        if df is None or df.empty:
            continue
        df = df.reset_index()
        # 컬럼: 티커, 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률
        df = df.rename(columns={
            "티커": "ticker",
            "시가": "open", "고가": "high", "저가": "low", "종가": "close",
            "거래량": "volume", "거래대금": "value",
        })
        df["date"] = date_iso
        keep = [c for c in ["ticker", "date", "open", "high", "low", "close", "volume", "value"] if c in df.columns]
        frames.append(df[keep])
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ── 재무 지표 ────────────────────────────────────────────────────────────────

def collect_fundamentals(target_date: date | str) -> pd.DataFrame:
    """KOSPI + KOSDAQ 전 종목 PER/PBR. 컬럼: ticker, date, per, pbr, eps, bps, div_yield, roe."""
    d = _date_str(target_date)
    date_iso = _iso(d)
    frames = []
    for market in ("KOSPI", "KOSDAQ"):
        df = _retry(stock.get_market_fundamental_by_ticker, d, market=market)
        if df is None or df.empty:
            continue
        df = df.reset_index()
        # 컬럼: 티커, BPS, PER, PBR, EPS, DIV, DPS
        df = df.rename(columns={
            "티커": "ticker",
            "BPS": "bps", "PER": "per", "PBR": "pbr",
            "EPS": "eps", "DIV": "div_yield", "DPS": "dps",
        })
        df["date"] = date_iso
        df["roe"] = None
        keep = [c for c in ["ticker", "date", "per", "pbr", "eps", "bps", "div_yield", "roe"] if c in df.columns]
        frames.append(df[keep])
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    for col in ["per", "pbr", "eps", "bps", "div_yield"]:
        if col in result.columns:
            result[col] = result[col].replace(0, None)
    return result


# ── 시장 지수 ────────────────────────────────────────────────────────────────

def get_index_ohlcv(start: str, end: str, ticker: str = "1001") -> pd.DataFrame:
    """지수 일봉. ticker 기본값 1001=KOSPI. 컬럼: date(YYYY-MM-DD), close."""
    d_start = _date_str(start)
    d_end = _date_str(end)
    try:
        df = stock.get_index_ohlcv_by_date(d_start, d_end, ticker)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    close_col = next((c for c in df.columns if str(c) in {"종가", "Close", "close"}), None)
    if close_col is None:
        return pd.DataFrame()
    date_col = df.columns[0]  # reset_index 후 첫 번째 컬럼이 날짜
    result = pd.DataFrame({"date": df[date_col], "close": df[close_col]})
    result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    return result.sort_values("date").reset_index(drop=True)


def get_market_ma20_valid_dates(start: str, end: str, index_ticker: str = "1001") -> frozenset[str]:
    """지수 종가 > MA20인 날짜 집합. 시장 필터 진입 조건으로 사용."""
    df = get_index_ohlcv(start, end, index_ticker)
    if df.empty:
        return frozenset()
    df["ma20"] = df["close"].rolling(20).mean()
    valid = df.dropna(subset=["ma20"])
    valid = valid[valid["close"] > valid["ma20"]]["date"]
    return frozenset(valid.tolist())


# ── 종목 정보 ────────────────────────────────────────────────────────────────

def collect_ticker_info() -> pd.DataFrame:
    """KOSPI + KOSDAQ 전 종목 기본 정보. 컬럼: ticker, name, market, sector, market_cap."""
    today = _date_str(date.today())
    frames = []
    for market in ("KOSPI", "KOSDAQ"):
        # 시가총액과 종목명을 한 번에 가져옴
        cap_df = _retry(stock.get_market_cap_by_ticker, today, market=market)
        if cap_df is None or cap_df.empty:
            continue
        cap_df = cap_df.reset_index()
        # 컬럼: 티커, 종목명, 시가총액, ...
        cap_df = cap_df.rename(columns={"티커": "ticker", "종목명": "name", "시가총액": "market_cap"})
        cap_df["market"] = market
        cap_df["sector"] = None
        keep = [c for c in ["ticker", "name", "market", "sector", "market_cap"] if c in cap_df.columns]
        frames.append(cap_df[keep])

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    # name 컬럼이 없으면 ticker_name API로 보완
    if "name" not in df.columns or df["name"].isna().all():
        df["name"] = df["ticker"].apply(lambda t: stock.get_market_ticker_name(t))
    return df[["ticker", "name", "market", "sector", "market_cap"]]
