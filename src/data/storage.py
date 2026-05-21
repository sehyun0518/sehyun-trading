"""PostgreSQL I/O — 모든 UPSERT/조회 함수.

DATABASE_URL 환경변수가 없으면 SQLite fallback (로컬 개발용).
"""
import json
import os
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator

import pandas as pd

_DATABASE_URL = os.getenv("DATABASE_URL")
_USE_PG = bool(_DATABASE_URL)

if not _USE_PG:
    import sqlite3
    import yaml

    def _db_path() -> Path:
        root = Path(__file__).parent.parent.parent
        with open(root / "config" / "settings.yaml") as f:
            settings = yaml.safe_load(f)
        return root / settings["database"]["path"]


@contextmanager
def _conn():
    if _USE_PG:
        import psycopg2
        conn = psycopg2.connect(_DATABASE_URL)
    else:
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


def _ph() -> str:
    """플레이스홀더: PostgreSQL=%s, SQLite=?"""
    return "%s" if _USE_PG else "?"


def _read(sql: str, params=None) -> pd.DataFrame:
    with _conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


# ── OHLCV ──────────────────────────────────────────────────────────────────

def upsert_ohlcv(df: pd.DataFrame) -> int:
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "value"]
    records = [tuple(r) for r in df[cols].values.tolist()]
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO daily_ohlcv (ticker, date, open, high, low, close, volume, value)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p})
            ON CONFLICT (ticker, date) DO UPDATE SET
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                close=EXCLUDED.close, volume=EXCLUDED.volume, value=EXCLUDED.value
        """
    else:
        sql = "INSERT OR REPLACE INTO daily_ohlcv (ticker,date,open,high,low,close,volume,value) VALUES (?,?,?,?,?,?,?,?)"
    with _conn() as conn:
        cur = conn.cursor()
        cur.executemany(sql, records)
    return len(records)


def get_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    p = _ph()
    sql = f"SELECT date,open,high,low,close,volume,value FROM daily_ohlcv WHERE ticker={p} AND date BETWEEN {p} AND {p} ORDER BY date"
    return _read(sql, (ticker, start, end))


def get_ohlcv_multi(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    p = _ph()
    placeholders = ",".join([p] * len(tickers))
    sql = f"SELECT ticker,date,open,high,low,close,volume,value FROM daily_ohlcv WHERE ticker IN ({placeholders}) AND date BETWEEN {p} AND {p} ORDER BY ticker,date"
    return _read(sql, (*tickers, start, end))


# ── 종목 정보 ────────────────────────────────────────────────────────────────

def upsert_ticker_info(df: pd.DataFrame) -> int:
    now = datetime.now().isoformat()
    records = [(row["ticker"], row["name"], row.get("market"), row.get("sector"), row.get("market_cap"), now)
               for _, row in df.iterrows()]
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO ticker_info (ticker,name,market,sector,market_cap,updated_at)
            VALUES ({p},{p},{p},{p},{p},{p})
            ON CONFLICT (ticker) DO UPDATE SET
                name=EXCLUDED.name, market=EXCLUDED.market, sector=EXCLUDED.sector,
                market_cap=EXCLUDED.market_cap, updated_at=EXCLUDED.updated_at
        """
    else:
        sql = "INSERT OR REPLACE INTO ticker_info (ticker,name,market,sector,market_cap,updated_at) VALUES (?,?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().executemany(sql, records)
    return len(records)


def get_universe() -> pd.DataFrame:
    return _read("SELECT * FROM ticker_info")


# ── 재무 지표 ────────────────────────────────────────────────────────────────

def upsert_fundamentals(df: pd.DataFrame) -> int:
    cols = ["ticker", "date", "per", "pbr", "eps", "bps", "div_yield", "roe"]
    records = [tuple(r) for r in df[cols].values.tolist()]
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO fundamentals (ticker,date,per,pbr,eps,bps,div_yield,roe)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p})
            ON CONFLICT (ticker,date) DO UPDATE SET
                per=EXCLUDED.per, pbr=EXCLUDED.pbr, eps=EXCLUDED.eps,
                bps=EXCLUDED.bps, div_yield=EXCLUDED.div_yield, roe=EXCLUDED.roe
        """
    else:
        sql = "INSERT OR REPLACE INTO fundamentals (ticker,date,per,pbr,eps,bps,div_yield,roe) VALUES (?,?,?,?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().executemany(sql, records)
    return len(records)


def get_fundamentals(ticker: str) -> pd.DataFrame:
    p = _ph()
    return _read(f"SELECT * FROM fundamentals WHERE ticker={p} ORDER BY date DESC", (ticker,))


# ── 수급 ────────────────────────────────────────────────────────────────────

def upsert_trading_flow(df: pd.DataFrame) -> int:
    cols = ["ticker", "date", "foreign_net", "inst_net", "indiv_net"]
    records = [tuple(r) for r in df[cols].values.tolist()]
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO trading_flow (ticker,date,foreign_net,inst_net,indiv_net)
            VALUES ({p},{p},{p},{p},{p})
            ON CONFLICT (ticker,date) DO UPDATE SET
                foreign_net=EXCLUDED.foreign_net, inst_net=EXCLUDED.inst_net,
                indiv_net=EXCLUDED.indiv_net
        """
    else:
        sql = "INSERT OR REPLACE INTO trading_flow (ticker,date,foreign_net,inst_net,indiv_net) VALUES (?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().executemany(sql, records)
    return len(records)


def get_trading_flow(ticker: str, days: int = 20) -> pd.DataFrame:
    p = _ph()
    return _read(f"SELECT * FROM trading_flow WHERE ticker={p} ORDER BY date DESC LIMIT {days}", (ticker,))


# ── 보유 종목 ────────────────────────────────────────────────────────────────

def upsert_holdings(df: pd.DataFrame) -> int:
    now = datetime.now().isoformat()
    records = [(row["ticker"], row["quantity"], row["avg_price"], row["current_price"],
                row["eval_amount"], row["eval_pl"], row["eval_pl_pct"], now)
               for _, row in df.iterrows()]
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO holdings (ticker,quantity,avg_price,current_price,eval_amount,eval_pl,eval_pl_pct,updated_at)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p})
            ON CONFLICT (ticker) DO UPDATE SET
                quantity=EXCLUDED.quantity, avg_price=EXCLUDED.avg_price,
                current_price=EXCLUDED.current_price, eval_amount=EXCLUDED.eval_amount,
                eval_pl=EXCLUDED.eval_pl, eval_pl_pct=EXCLUDED.eval_pl_pct,
                updated_at=EXCLUDED.updated_at
        """
    else:
        sql = "INSERT OR REPLACE INTO holdings (ticker,quantity,avg_price,current_price,eval_amount,eval_pl,eval_pl_pct,updated_at) VALUES (?,?,?,?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().executemany(sql, records)
    return len(records)


def get_holdings() -> pd.DataFrame:
    return _read("SELECT * FROM holdings")


# ── 리포트 ───────────────────────────────────────────────────────────────────

def save_report_meta(report_date: date, candidates: list, warnings: list,
                     file_path: str, content: str = "") -> None:
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO reports (report_date,candidates,warnings,file_path,content)
            VALUES ({p},{p},{p},{p},{p})
            ON CONFLICT (report_date) DO UPDATE SET
                candidates=EXCLUDED.candidates, warnings=EXCLUDED.warnings,
                file_path=EXCLUDED.file_path, content=EXCLUDED.content
        """
    else:
        sql = "INSERT OR REPLACE INTO reports (report_date,candidates,warnings,file_path,content) VALUES (?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().execute(sql, (
            report_date.isoformat(),
            json.dumps(candidates, ensure_ascii=False),
            json.dumps(warnings, ensure_ascii=False),
            file_path,
            content,
        ))


def get_reports(limit: int = 20) -> pd.DataFrame:
    return _read(f"SELECT report_date, candidates, warnings, file_path FROM reports ORDER BY report_date DESC LIMIT {limit}")


def get_report_content(report_date: str) -> dict | None:
    p = _ph()
    df = _read(f"SELECT * FROM reports WHERE report_date={p}", (report_date,))
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "date": row["report_date"],
        "content": row.get("content", ""),
        "candidates": json.loads(row["candidates"] or "[]"),
        "warnings": json.loads(row["warnings"] or "[]"),
        "file_path": row.get("file_path", ""),
    }
