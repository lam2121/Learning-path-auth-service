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


# ── RS256 Key Loading ─────────────────────────────────────────────────────────

_project_root = Path(__file__).resolve().parents[2]


def _load_key(relative_path: str) -> str:
    key_path = _project_root / relative_path
    return key_path.read_text()


_private_key: str | None = None
_public_key: str | None = None


def get_private_key() -> str:
    global _private_key
    if _private_key is None:
        _private_key = _load_key(app_config.RSA_PRIVATE_KEY_PATH)
    return _private_key


def get_public_key() -> str:
    global _public_key
    if _public_key is None:
        _public_key = _load_key(app_config.RSA_PUBLIC_KEY_PATH)
    return _public_key



def create_access_token(data: dict) -> str:
    """Create a short-lived RS256 access token (default 30 min)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=app_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "iss": app_config.JWT_ISSUER,
        "aud": app_config.JWT_AUDIENCE.split(","),
        "jti": uuid.uuid4().hex,
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    return jwt.encode(to_encode, get_private_key(), algorithm="RS256")


def create_refresh_token(data: dict) -> str:
    """Create a long-lived RS256 refresh token (default 7 days)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=app_config.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "iss": app_config.JWT_ISSUER,
        "aud": app_config.JWT_AUDIENCE.split(","),
        "jti": uuid.uuid4().hex,
        "token_type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    return jwt.encode(to_encode, get_private_key(), algorithm="RS256")


# ── JWT Verification ─────────────────────────────────────────────────────────

def verify_token(token: str, expected_type: str = "access", expected_audience: str | None = None) -> dict | None:
    """Decode and validate an RS256 JWT token.

    Returns the payload dict on success, or ``None`` if the token is invalid,
    expired, or has the wrong ``token_type``.
    """
    try:
        # python-jose requires `audience` to be a string, not a list.
        # The token's "aud" is a list like ["toeic", "careerpath"].
        # We try each configured audience until decode succeeds.
        configured_audiences = app_config.JWT_AUDIENCE.split(",")

        payload = None
        last_error = None
        for aud in configured_audiences:
            try:
                payload = jwt.decode(
                    token,
                    get_public_key(),
                    algorithms=["RS256"],
                    issuer=app_config.JWT_ISSUER,
                    audience=aud.strip(),
                )
                break  # decode succeeded
            except JWTError as e:
                last_error = e
                continue

        if payload is None:
            return None

        if payload.get("token_type") != expected_type:
            return None

        # Additional audience check if a specific audience is expected
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
