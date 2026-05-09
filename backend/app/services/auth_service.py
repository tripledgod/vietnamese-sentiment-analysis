"""
JWT và mật khẩu (bcrypt).
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, password_hash: str | bytes | None) -> bool:
    if plain is None or password_hash is None:
        return False
    try:
        if isinstance(password_hash, bytes):
            hashed = password_hash.strip()
        else:
            hashed = str(password_hash).strip().encode("ascii")
        return bcrypt.checkpw(plain.encode("utf-8"), hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    user_id: int,
    username: str,
    role: str,
    must_change_password: bool,
) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "must_change_password": 1 if must_change_password else 0,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
