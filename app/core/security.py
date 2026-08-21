"""RS256 JWT signing / verification and Bcrypt password hashing."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import app_config

# ── Bcrypt ────────────────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ── HS256 Token Creation ──────────────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    """Create a short-lived HS256 access token (default 30 min)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=app_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "iss": app_config.JWT_ISSUER,
        "aud": [a.strip() for a in app_config.JWT_AUDIENCE.split(",")],
        "jti": uuid.uuid4().hex,
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    return jwt.encode(to_encode, app_config.JWT_SECRET_KEY, algorithm=app_config.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived HS256 refresh token (default 7 days)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=app_config.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "iss": app_config.JWT_ISSUER,
        "aud": [a.strip() for a in app_config.JWT_AUDIENCE.split(",")],
        "jti": uuid.uuid4().hex,
        "token_type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    return jwt.encode(to_encode, app_config.JWT_SECRET_KEY, algorithm=app_config.JWT_ALGORITHM)


# ── JWT Verification ─────────────────────────────────────────────────────────

def verify_token(token: str, expected_type: str = "access", expected_audience: str | None = None) -> dict | None:
    """Decode and validate an HS256 JWT token.

    Returns the payload dict on success, or ``None`` if the token is invalid,
    expired, or has the wrong ``token_type``.
    """
    try:
        configured_audiences = [a.strip() for a in app_config.JWT_AUDIENCE.split(",")]
        payload = None
        for aud in configured_audiences:
            try:
                payload = jwt.decode(
                    token,
                    app_config.JWT_SECRET_KEY,
                    algorithms=[app_config.JWT_ALGORITHM],
                    issuer=app_config.JWT_ISSUER,
                    audience=aud,
                )
                break  # decode succeeded
            except JWTError:
                continue

        if payload is None:
            return None

        if payload.get("token_type") != expected_type:
            return None

        if expected_audience:
            token_aud = payload.get("aud")
            if isinstance(token_aud, list):
                if expected_audience not in token_aud:
                    return None
            elif isinstance(token_aud, str):
                if expected_audience != token_aud:
                    return None

        return payload
    except JWTError:
        return None


# ── Refresh Token Hash ────────────────────────────────────────────────────────

def hash_refresh_token(raw_token: str) -> str:
    """SHA-256 hash of the raw refresh token for DB storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
