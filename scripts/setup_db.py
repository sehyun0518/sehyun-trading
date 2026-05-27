"""DB 초기화 — PostgreSQL(DATABASE_URL) 또는 SQLite(로컬).

실행:
    uv run python scripts/setup_db.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

ROOT = Path(__file__).parent.parent
DATABASE_URL = os.getenv("DATABASE_URL")

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    ticker TEXT NOT NULL, date DATE NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER, value INTEGER,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv(date);
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv(ticker);
CREATE TABLE IF NOT EXISTS ticker_info (
    ticker TEXT PRIMARY KEY, name TEXT NOT NULL,
    market TEXT, sector TEXT, market_cap INTEGER, updated_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker TEXT NOT NULL, date DATE NOT NULL,
    per REAL, pbr REAL, eps REAL, bps REAL, div_yield REAL, roe REAL,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS trading_flow (
    ticker TEXT NOT NULL, date DATE NOT NULL,
    foreign_net REAL, inst_net REAL, indiv_net REAL,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS holdings (
    ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price REAL,
    current_price REAL, eval_amount INTEGER, eval_pl INTEGER,
    eval_pl_pct REAL, updated_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
    report_date DATE PRIMARY KEY, candidates TEXT, warnings TEXT,
    file_path TEXT, content TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    kis_paper_key_enc TEXT,
    kis_paper_secret_enc TEXT,
    kis_paper_account TEXT,
    kis_real_key_enc TEXT,
    kis_real_secret_enc TEXT,
    kis_real_account TEXT,
    notify_slack_webhook TEXT,
    notify_discord_webhook TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ticker TEXT NOT NULL,
    name TEXT,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    price REAL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    kis_order_no TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE TABLE IF NOT EXISTS candidate_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_date DATE NOT NULL,
    ticker TEXT NOT NULL,
    name TEXT,
    source TEXT NOT NULL DEFAULT 'candidates',
    indicators TEXT NOT NULL,
    entry_checks TEXT NOT NULL,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, run_date, ticker, source)
);
CREATE INDEX IF NOT EXISTS idx_candidate_snapshots_user_date ON candidate_snapshots(user_id, run_date DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_snapshots_ticker ON candidate_snapshots(ticker);
"""

PG_DDL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS daily_ohlcv (
        ticker TEXT NOT NULL, date DATE NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume BIGINT, value BIGINT,
        PRIMARY KEY (ticker, date))""",
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_date   ON daily_ohlcv(date)",
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv(ticker)",
    """CREATE TABLE IF NOT EXISTS ticker_info (
        ticker TEXT PRIMARY KEY, name TEXT NOT NULL,
        market TEXT, sector TEXT, market_cap BIGINT, updated_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS fundamentals (
        ticker TEXT NOT NULL, date DATE NOT NULL,
        per REAL, pbr REAL, eps REAL, bps REAL, div_yield REAL, roe REAL,
        PRIMARY KEY (ticker, date))""",
    """CREATE TABLE IF NOT EXISTS trading_flow (
        ticker TEXT NOT NULL, date DATE NOT NULL,
        foreign_net REAL, inst_net REAL, indiv_net REAL,
        PRIMARY KEY (ticker, date))""",
    """CREATE TABLE IF NOT EXISTS holdings (
        ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price REAL,
        current_price REAL, eval_amount BIGINT, eval_pl BIGINT,
        eval_pl_pct REAL, updated_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS reports (
        report_date DATE PRIMARY KEY, candidates TEXT, warnings TEXT,
        file_path TEXT, content TEXT)""",
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        kis_paper_key_enc TEXT,
        kis_paper_secret_enc TEXT,
        kis_paper_account VARCHAR(20),
        kis_real_key_enc TEXT,
        kis_real_secret_enc TEXT,
        kis_real_account VARCHAR(20),
        notify_slack_webhook TEXT,
        notify_discord_webhook TEXT)""",
    """CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        ticker TEXT NOT NULL,
        name TEXT,
        side TEXT NOT NULL,
        qty INTEGER NOT NULL,
        price REAL,
        executed_at TIMESTAMP DEFAULT NOW(),
        kis_order_no TEXT)""",
    "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)",
    """CREATE TABLE IF NOT EXISTS candidate_snapshots (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        run_date DATE NOT NULL,
        ticker TEXT NOT NULL,
        name TEXT,
        source TEXT NOT NULL DEFAULT 'candidates',
        indicators TEXT NOT NULL,
        entry_checks TEXT NOT NULL,
        entry_price REAL,
        stop_loss REAL,
        take_profit REAL,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (user_id, run_date, ticker, source))""",
    "CREATE INDEX IF NOT EXISTS idx_candidate_snapshots_user_date ON candidate_snapshots(user_id, run_date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_candidate_snapshots_ticker ON candidate_snapshots(ticker)",
]


def setup_pg() -> None:
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    for stmt in PG_DDL_STATEMENTS:
        cur.execute(stmt)
    conn.commit()
    conn.close()
    host = DATABASE_URL.split("@")[-1]
    print(f"✓ PostgreSQL 스키마 초기화 완료 ({host})")


def setup_sqlite() -> None:
    import sqlite3
    import yaml
    with open(ROOT / "config" / "settings.yaml") as f:
        settings = yaml.safe_load(f)
    db_path = ROOT / settings["database"]["path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SQLITE_DDL)
    conn.commit()
    conn.close()
    print(f"✓ SQLite 스키마 초기화 완료 ({db_path})")


if __name__ == "__main__":
    if DATABASE_URL:
        setup_pg()
    else:
        setup_sqlite()
