"""PostgreSQL → S3 일일 백업 스크립트.

실행: uv run python scripts/backup_db.py
cron: 0 3 * * * (매일 03:00 UTC = 12:00 KST)
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
S3_BUCKET = os.getenv("BACKUP_S3_BUCKET", "")

if not DATABASE_URL:
    print("DATABASE_URL이 설정되지 않았습니다.")
    sys.exit(1)
if not S3_BUCKET:
    print("BACKUP_S3_BUCKET이 설정되지 않았습니다.")
    sys.exit(1)

timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
filename = f"trading_db_{timestamp}.sql.gz"
local_path = f"/tmp/{filename}"
s3_key = f"backups/{filename}"

print(f"[1/3] pg_dump 실행: {filename}")
result = subprocess.run(
    ["pg_dump", DATABASE_URL, "--no-password"],
    capture_output=True,
)
if result.returncode != 0:
    print(f"pg_dump 실패: {result.stderr.decode()}")
    sys.exit(1)

import gzip
with gzip.open(local_path, "wb") as f:
    f.write(result.stdout)
print(f"[2/3] 압축 완료: {local_path}")

print(f"[3/3] S3 업로드: s3://{S3_BUCKET}/{s3_key}")
upload = subprocess.run(
    ["aws", "s3", "cp", local_path, f"s3://{S3_BUCKET}/{s3_key}",
     "--storage-class", "STANDARD"],
    capture_output=True,
)
if upload.returncode != 0:
    print(f"S3 업로드 실패: {upload.stderr.decode()}")
    sys.exit(1)

os.remove(local_path)
print(f"✓ 백업 완료: s3://{S3_BUCKET}/{s3_key}")
