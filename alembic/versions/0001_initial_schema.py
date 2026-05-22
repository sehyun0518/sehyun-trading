"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-22
"""
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            ticker TEXT NOT NULL, date DATE NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume BIGINT, value BIGINT,
            PRIMARY KEY (ticker, date))
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_date   ON daily_ohlcv(date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv(ticker)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS ticker_info (
            ticker TEXT PRIMARY KEY, name TEXT NOT NULL,
            market TEXT, sector TEXT, market_cap BIGINT, updated_at TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT NOT NULL, date DATE NOT NULL,
            per REAL, pbr REAL, eps REAL, bps REAL, div_yield REAL, roe REAL,
            PRIMARY KEY (ticker, date))
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS trading_flow (
            ticker TEXT NOT NULL, date DATE NOT NULL,
            foreign_net REAL, inst_net REAL, indiv_net REAL,
            PRIMARY KEY (ticker, date))
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price REAL,
            current_price REAL, eval_amount BIGINT, eval_pl BIGINT,
            eval_pl_pct REAL, updated_at TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_date DATE PRIMARY KEY, candidates TEXT, warnings TEXT,
            file_path TEXT, content TEXT)
    """)


def downgrade() -> None:
    for t in ("reports", "holdings", "trading_flow", "fundamentals", "ticker_info", "daily_ohlcv"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
