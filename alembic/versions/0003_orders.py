"""orders table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-22
"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER,
            ticker     TEXT NOT NULL,
            name       TEXT,
            side       TEXT NOT NULL,
            qty        INTEGER NOT NULL,
            price      REAL,
            executed_at TIMESTAMP DEFAULT NOW(),
            kis_order_no TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS orders")
