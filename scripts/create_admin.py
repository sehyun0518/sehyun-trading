"""최초 관리자 계정 생성 스크립트.

실행: uv run python scripts/create_admin.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import getpass
from src.data import storage
from src.api.auth import hash_password

email = input("관리자 이메일: ").strip().lower()
password = getpass.getpass("패스워드 (8자 이상): ")

if len(password) < 8:
    print("패스워드는 8자 이상이어야 합니다.")
    sys.exit(1)

if storage.get_user_by_email(email):
    print(f"이미 존재하는 이메일: {email}")
    sys.exit(1)

user_id = storage.create_user(email, hash_password(password))
print(f"✓ 관리자 계정 생성 완료 (id={user_id}, email={email})")
print("기존 holdings/reports는 이 계정(user_id=1)에 자동 귀속됩니다.")
