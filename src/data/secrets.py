"""Fernet 대칭 암호화 — KIS 자격증명 DB 저장용."""
import os

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    key = os.getenv("FERNET_KEY", "")
    if not key:
        raise RuntimeError("FERNET_KEY 환경변수가 설정되지 않았습니다.")
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode()).decode()
