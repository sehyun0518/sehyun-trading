"""JWT 인증 — 유저 이메일/패스워드 기반."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30
_bearer = HTTPBearer()


def _jwt_secret() -> str:
    s = os.getenv("JWT_SECRET", "")
    if not s:
        raise RuntimeError("JWT_SECRET 환경변수가 설정되지 않았습니다.")
    return s


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "exp": expire},
        _jwt_secret(),
        algorithm=_ALGORITHM,
    )


def verify_token(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, _jwt_secret(), algorithms=[_ALGORITHM])
        return {"id": int(payload["sub"]), "email": payload["email"]}
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")
