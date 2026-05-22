"""JWT 인증 — 단일 관리자 패스워드 기반."""
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30
_bearer = HTTPBearer()


def _jwt_secret() -> str:
    s = os.getenv("JWT_SECRET", "")
    if not s:
        raise RuntimeError("JWT_SECRET 환경변수가 설정되지 않았습니다.")
    return s


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode({"sub": "admin", "exp": expire}, _jwt_secret(), algorithm=_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, _jwt_secret(), algorithms=[_ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")


def check_password(password: str) -> bool:
    expected = os.getenv("ADMIN_PASSWORD", "")
    if not expected:
        return False
    return secrets.compare_digest(password.encode(), expected.encode())
