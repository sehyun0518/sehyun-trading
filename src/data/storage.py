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


def get_trading_flow_multi(tickers: list[str], days: int = 10) -> pd.DataFrame:
    """여러 종목의 수급을 한 번에 조회."""
    if not tickers:
        return pd.DataFrame()
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=days * 3)).isoformat()
    p = _ph()
    placeholders = ",".join([p] * len(tickers))
    sql = (
        f"SELECT ticker,date,foreign_net,inst_net,indiv_net FROM trading_flow "
        f"WHERE ticker IN ({placeholders}) AND date >= {p} ORDER BY ticker, date DESC"
    )
    return _read(sql, (*tickers, cutoff))


# ── 유저 ─────────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str) -> int:
    p = _ph()
    if _USE_PG:
        sql = f"INSERT INTO users (email, password_hash) VALUES ({p},{p}) RETURNING id"
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (email, password_hash))
            return cur.fetchone()[0]
    else:
        sql = f"INSERT INTO users (email, password_hash) VALUES ({p},{p})"
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (email, password_hash))
            return cur.lastrowid


def get_user_by_email(email: str) -> dict | None:
    p = _ph()
    df = _read(f"SELECT * FROM users WHERE email={p}", (email,))
    if df.empty:
        return None
    row = df.iloc[0]
    return row.to_dict()


def get_user_by_id(user_id: int) -> dict | None:
    p = _ph()
    df = _read(f"SELECT * FROM users WHERE id={p}", (user_id,))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def update_user_kis(user_id: int, fields: dict) -> None:
    """KIS 자격증명 + 알림 webhook 업데이트."""
    p = _ph()
    allowed = {
        "kis_paper_key_enc", "kis_paper_secret_enc", "kis_paper_account",
        "kis_real_key_enc", "kis_real_secret_enc", "kis_real_account",
        "notify_slack_webhook", "notify_discord_webhook",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}={p}" for k in updates)
    sql = f"UPDATE users SET {set_clause} WHERE id={p}"
    with _conn() as conn:
        conn.cursor().execute(sql, (*updates.values(), user_id))


# ── 보유 종목 ────────────────────────────────────────────────────────────────

def upsert_holdings(df: pd.DataFrame, user_id: int = 1) -> int:
    now = datetime.now().isoformat()
    records = [(row["ticker"], row["quantity"], row["avg_price"], row["current_price"],
                row["eval_amount"], row["eval_pl"], row["eval_pl_pct"], now, user_id)
               for _, row in df.iterrows()]
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO holdings (ticker,quantity,avg_price,current_price,eval_amount,eval_pl,eval_pl_pct,updated_at,user_id)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p})
            ON CONFLICT (ticker) DO UPDATE SET
                quantity=EXCLUDED.quantity, avg_price=EXCLUDED.avg_price,
                current_price=EXCLUDED.current_price, eval_amount=EXCLUDED.eval_amount,
                eval_pl=EXCLUDED.eval_pl, eval_pl_pct=EXCLUDED.eval_pl_pct,
                updated_at=EXCLUDED.updated_at, user_id=EXCLUDED.user_id
        """
    else:
        sql = "INSERT OR REPLACE INTO holdings (ticker,quantity,avg_price,current_price,eval_amount,eval_pl,eval_pl_pct,updated_at,user_id) VALUES (?,?,?,?,?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().executemany(sql, records)
    return len(records)


def get_holdings(user_id: int = 1) -> pd.DataFrame:
    p = _ph()
    return _read(f"SELECT * FROM holdings WHERE user_id={p}", (user_id,))


# ── 리포트 ───────────────────────────────────────────────────────────────────

def save_report_meta(report_date: date, candidates: list, warnings: list,
                     file_path: str, content: str = "", user_id: int = 1) -> None:
    p = _ph()
    if _USE_PG:
        sql = f"""
            INSERT INTO reports (report_date,candidates,warnings,file_path,content,user_id)
            VALUES ({p},{p},{p},{p},{p},{p})
            ON CONFLICT (report_date) DO UPDATE SET
                candidates=EXCLUDED.candidates, warnings=EXCLUDED.warnings,
                file_path=EXCLUDED.file_path, content=EXCLUDED.content,
                user_id=EXCLUDED.user_id
        """
    else:
        sql = "INSERT OR REPLACE INTO reports (report_date,candidates,warnings,file_path,content,user_id) VALUES (?,?,?,?,?,?)"
    with _conn() as conn:
        conn.cursor().execute(sql, (
            report_date.isoformat(),
            json.dumps(candidates, ensure_ascii=False),
            json.dumps(warnings, ensure_ascii=False),
            file_path,
            content,
            user_id,
        ))


def get_reports(limit: int = 20, user_id: int = 1) -> pd.DataFrame:
    p = _ph()
    return _read(
        f"SELECT report_date, candidates, warnings, file_path FROM reports WHERE user_id={p} ORDER BY report_date DESC LIMIT {limit}",
        (user_id,)
    )


def get_report_content(report_date: str, user_id: int = 1) -> dict | None:
    p = _ph()
    df = _read(f"SELECT * FROM reports WHERE report_date={p} AND user_id={p}", (report_date, user_id))
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


# ── 주문 히스토리 ──────────────────────────────────────────────────────────────

def save_order(user_id: int, ticker: str, name: str, side: str,
               qty: int, price: float, kis_order_no: str = "") -> None:
    p = _ph()
    now = datetime.now().isoformat()
    sql = f"""
        INSERT INTO orders (user_id, ticker, name, side, qty, price, executed_at, kis_order_no)
        VALUES ({p},{p},{p},{p},{p},{p},{p},{p})
    """
    with _conn() as conn:
        conn.cursor().execute(sql, (user_id, ticker, name, side, qty, price, now, kis_order_no))


def get_orders(user_id: int, limit: int = 50) -> pd.DataFrame:
    p = _ph()
    return _read(
        f"SELECT * FROM orders WHERE user_id={p} ORDER BY executed_at DESC LIMIT {limit}",
        (user_id,)
    )


# ── 엔진 캐시 ─────────────────────────────────────────────────────────────────

_CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "engine_cache.json"


def save_engine_cache(result: dict) -> None:
    _CACHE_PATH.parent.mkdir(exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(result, ensure_ascii=False, default=str))


def get_engine_cache() -> dict | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        return json.loads(_CACHE_PATH.read_text())
    except Exception:
        return None
