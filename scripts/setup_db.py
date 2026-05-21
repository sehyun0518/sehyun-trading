"""초기 SQLite 스키마 생성. 멱등 (CREATE TABLE IF NOT EXISTS)."""
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent


def get_db_path() -> Path:
    with open(ROOT / "config" / "settings.yaml") as f:
        settings = yaml.safe_load(f)
    return ROOT / settings["database"]["path"]


DDL = """
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      INTEGER,
    value       INTEGER,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv(date);
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv(ticker);

CREATE TABLE IF NOT EXISTS ticker_info (
    ticker      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    market      TEXT,
    sector      TEXT,
    market_cap  INTEGER,
    updated_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fundamentals (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    per         REAL,
    pbr         REAL,
    eps         REAL,
    bps         REAL,
    div_yield   REAL,
    roe         REAL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS trading_flow (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    foreign_net REAL,
    inst_net    REAL,
    indiv_net   REAL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS holdings (
    ticker        TEXT PRIMARY KEY,
    quantity      INTEGER,
    avg_price     REAL,
    current_price REAL,
    eval_amount   INTEGER,
    eval_pl       INTEGER,
    eval_pl_pct   REAL,
    updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    report_date DATE PRIMARY KEY,
    candidates  TEXT,
    warnings    TEXT,
    file_path   TEXT
);
"""


def setup():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    conn.commit()
    conn.close()

    print(f"DB initialized: {db_path}")
    print("Tables: daily_ohlcv, ticker_info, fundamentals, trading_flow, holdings, reports")


if __name__ == "__main__":
    setup()
