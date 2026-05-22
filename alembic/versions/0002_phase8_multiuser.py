"""phase 8 multiuser: users table, user_id FK

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22
"""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            kis_paper_key_enc  TEXT,
            kis_paper_secret_enc TEXT,
            kis_paper_account  VARCHAR(20),
            kis_real_key_enc   TEXT,
            kis_real_secret_enc TEXT,
            kis_real_account   VARCHAR(20),
            notify_slack_webhook  TEXT,
            notify_discord_webhook TEXT
        )
    """)

    # holdings/reports에 user_id 추가 (FK 없이 — 관리자 계정 생성 후 backfill)
    op.execute("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS user_id INTEGER")
    op.execute("ALTER TABLE reports  ADD COLUMN IF NOT EXISTS user_id INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS user_id")
    op.execute("ALTER TABLE holdings DROP COLUMN IF EXISTS user_id")
    op.execute("DROP TABLE IF EXISTS users")
