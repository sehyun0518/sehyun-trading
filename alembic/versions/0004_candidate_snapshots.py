"""candidate snapshots for strategy review

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-27
"""
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS candidate_snapshots (
            id            SERIAL PRIMARY KEY,
            user_id       INTEGER NOT NULL,
            run_date      DATE NOT NULL,
            ticker        TEXT NOT NULL,
            name          TEXT,
            source        TEXT NOT NULL DEFAULT 'candidates',
            indicators    TEXT NOT NULL,
            entry_checks  TEXT NOT NULL,
            entry_price   REAL,
            stop_loss     REAL,
            take_profit   REAL,
            created_at    TIMESTAMP DEFAULT NOW(),
            UNIQUE (user_id, run_date, ticker, source)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_snapshots_user_date ON candidate_snapshots(user_id, run_date DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_snapshots_ticker ON candidate_snapshots(ticker)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS candidate_snapshots")
