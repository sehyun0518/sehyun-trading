"""rules.yaml 기준 종목 유니버스 필터링."""
from pathlib import Path

import pandas as pd
import yaml


def _load_rules() -> dict:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "rules.yaml") as f:
        return yaml.safe_load(f)


def filter_universe(ticker_info: pd.DataFrame) -> pd.DataFrame:
    """
    ticker_info: storage.get_universe() 결과
      컬럼: ticker, name, market, sector, market_cap
    반환: 유니버스 조건 통과 종목 DataFrame
    """
    rules = _load_rules()
    u = rules["universe"]
    df = ticker_info.copy()

    # 허용 마켓
    allowed_markets = [m.upper() for m in u.get("markets", ["KOSPI", "KOSDAQ"])]
    df = df[df["market"].str.upper().isin(allowed_markets)]

    # 최소 시가총액 (억 단위 → 원 단위 변환)
    min_cap = u.get("min_market_cap_billion", 0) * 1_0000_0000
    if min_cap > 0 and "market_cap" in df.columns:
        df = df[df["market_cap"].fillna(0) >= min_cap]

    # 제외 섹터
    exclude_sectors = u.get("exclude_sectors", [])
    if exclude_sectors and "sector" in df.columns:
        df = df[~df["sector"].isin(exclude_sectors)]

    # 수동 제외 종목
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "universe.yaml") as f:
        uni_cfg = yaml.safe_load(f)
    exclude_tickers = uni_cfg.get("exclude_tickers", []) or []
    if exclude_tickers:
        df = df[~df["ticker"].isin(exclude_tickers)]

    # 수동 포함 종목 추가 (유니버스 밖 관심종목)
    include_tickers = uni_cfg.get("include_tickers", []) or []
    if include_tickers:
        extra = ticker_info[ticker_info["ticker"].isin(include_tickers)]
        df = pd.concat([df, extra]).drop_duplicates(subset=["ticker"])

    return df.reset_index(drop=True)
