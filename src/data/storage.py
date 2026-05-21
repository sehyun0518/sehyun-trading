"""SQLite I/O — 모든 UPSERT/조회 함수."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator

import pandas as pd
import yaml


def _db_path() -> Path:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "settings.yaml") as f:
        settings = yaml.safe_load(f)
    return root / settings["database"]["path"]


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── OHLCV ──────────────────────────────────────────────────────────────────

def upsert_ohlcv(df: pd.DataFrame) -> int:
    """df: ticker, date, open, high, low, close, volume, value 컬럼 필수."""
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "value"]
    records = df[cols].values.tolist()
    sql = """
        INSERT OR REPLACE INTO daily_ohlcv
            (ticker, date, open, high, low, close, volume, value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _conn() as conn:
        conn.executemany(sql, records)
    return len(records)


def get_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    sql = """
        SELECT date, open, high, low, close, volume, value
        FROM daily_ohlcv
        WHERE ticker = ? AND date BETWEEN ? AND ?
        ORDER BY date
    """
    with _conn() as conn:
        df = pd.read_sql_query(sql, conn, params=(ticker, start, end), parse_dates=["date"])
    return df


def get_ohlcv_multi(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    placeholders = ",".join("?" * len(tickers))
    sql = f"""
        SELECT ticker, date, open, high, low, close, volume, value
        FROM daily_ohlcv
        WHERE ticker IN ({placeholders}) AND date BETWEEN ? AND ?
        ORDER BY ticker, date
    """
    with _conn() as conn:
        df = pd.read_sql_query(
            sql, conn, params=(*tickers, start, end), parse_dates=["date"]
        )
    return df


# ── 종목 정보 ────────────────────────────────────────────────────────────────

def upsert_ticker_info(df: pd.DataFrame) -> int:
    """df: ticker, name, market, sector, market_cap 컬럼."""
    records = []
    now = datetime.now().isoformat()
    for _, row in df.iterrows():
        records.append((
            row["ticker"], row["name"],
            row.get("market"), row.get("sector"),
            row.get("market_cap"), now,
        ))
    sql = """
        INSERT OR REPLACE INTO ticker_info
            (ticker, name, market, sector, market_cap, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    with _conn() as conn:
        conn.executemany(sql, records)
    return len(records)


def get_universe() -> pd.DataFrame:
    """ticker_info 전체 반환."""
    with _conn() as conn:
        return pd.read_sql_query("SELECT * FROM ticker_info", conn)


# ── 재무 지표 ────────────────────────────────────────────────────────────────

def upsert_fundamentals(df: pd.DataFrame) -> int:
    """df: ticker, date, per, pbr, eps, bps, div_yield, roe."""
    cols = ["ticker", "date", "per", "pbr", "eps", "bps", "div_yield", "roe"]
    records = df[cols].values.tolist()
    sql = """
        INSERT OR REPLACE INTO fundamentals
            (ticker, date, per, pbr, eps, bps, div_yield, roe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _conn() as conn:
        conn.executemany(sql, records)
    return len(records)


def get_fundamentals(ticker: str) -> pd.DataFrame:
    sql = "SELECT * FROM fundamentals WHERE ticker = ? ORDER BY date DESC"
    with _conn() as conn:
        return pd.read_sql_query(sql, conn, params=(ticker,), parse_dates=["date"])


# ── 수급 ────────────────────────────────────────────────────────────────────

def upsert_trading_flow(df: pd.DataFrame) -> int:
    """df: ticker, date, foreign_net, inst_net, indiv_net."""
    cols = ["ticker", "date", "foreign_net", "inst_net", "indiv_net"]
    records = df[cols].values.tolist()
    sql = """
        INSERT OR REPLACE INTO trading_flow
            (ticker, date, foreign_net, inst_net, indiv_net)
        VALUES (?, ?, ?, ?, ?)
    """
    with _conn() as conn:
        conn.executemany(sql, records)
    return len(records)


def get_trading_flow(ticker: str, days: int = 20) -> pd.DataFrame:
    sql = """
        SELECT * FROM trading_flow
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT ?
    """
    with _conn() as conn:
        return pd.read_sql_query(sql, conn, params=(ticker, days), parse_dates=["date"])


# ── 보유 종목 ────────────────────────────────────────────────────────────────

def upsert_holdings(df: pd.DataFrame) -> int:
    now = datetime.now().isoformat()
    records = []
    for _, row in df.iterrows():
        records.append((
            row["ticker"], row["quantity"], row["avg_price"],
            row["current_price"], row["eval_amount"],
            row["eval_pl"], row["eval_pl_pct"], now,
        ))
    sql = """
        INSERT OR REPLACE INTO holdings
            (ticker, quantity, avg_price, current_price,
             eval_amount, eval_pl, eval_pl_pct, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _conn() as conn:
        conn.executemany(sql, records)
    return len(records)


def get_holdings() -> pd.DataFrame:
    with _conn() as conn:
        return pd.read_sql_query("SELECT * FROM holdings", conn)


# ── 리포트 메타 ──────────────────────────────────────────────────────────────

def save_report_meta(
    report_date: date,
    candidates: list,
    warnings: list,
    file_path: str,
) -> None:
    sql = """
        INSERT OR REPLACE INTO reports (report_date, candidates, warnings, file_path)
        VALUES (?, ?, ?, ?)
    """
    with _conn() as conn:
        conn.execute(sql, (
            report_date.isoformat(),
            json.dumps(candidates, ensure_ascii=False),
            json.dumps(warnings, ensure_ascii=False),
            file_path,
        ))
