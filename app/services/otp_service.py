"""OTP generation, verification, and rate-limiting logic."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

from diskcache import Cache
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import app_config
from app.models.otp_rate_limit import OtpRateLimit

from jose import jwt

# ── Disk Cache for OTP storage ────────────────────────────────────────────────

import os as _os

_CACHE_DIR = _os.path.join(_os.path.dirname(__file__), "..", "..", "_otp_cache")
otp_cache = Cache(_CACHE_DIR)


# ── OTP Generation ────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


# ── Rate Limiting ─────────────────────────────────────────────────────────────

def check_otp_rate_limit(db: Session, email: str) -> None:
    """Raise 429 if the email has exceeded the OTP request limit."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start_threshold = now - timedelta(minutes=app_config.OTP_RATE_LIMIT_WINDOW_MINUTES)

    record = db.query(OtpRateLimit).filter(OtpRateLimit.email == email).first()

    if record is None:
        # First request ever — create tracking record
        record = OtpRateLimit(
            email=email,
            request_count=1,
            verify_attempts=0,
            window_start=now,
            last_attempt_at=now,
        )
        db.add(record)
        db.commit()
        return

    # If the window has expired, reset
    if record.window_start < window_start_threshold:
        record.request_count = 1
        record.verify_attempts = 0
        record.window_start = now
        record.last_attempt_at = now
        db.commit()
        return

    # Within the window — check limit
    if record.request_count >= app_config.OTP_MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quá nhiều yêu cầu OTP. Vui lòng thử lại sau {app_config.OTP_RATE_LIMIT_WINDOW_MINUTES} phút.",
        )

    record.request_count += 1
    record.last_attempt_at = now
    db.commit()


def check_verify_attempts(db: Session, email: str) -> None:
    """Raise 429 if too many OTP verify attempts."""
    record = db.query(OtpRateLimit).filter(OtpRateLimit.email == email).first()
    if record and record.verify_attempts >= app_config.OTP_MAX_VERIFY_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Quá nhiều lần nhập sai OTP. Vui lòng yêu cầu mã mới.",
        )


def increment_verify_attempts(db: Session, email: str) -> None:
    """Increment the verify attempt counter."""
    record = db.query(OtpRateLimit).filter(OtpRateLimit.email == email).first()
    if record:
        record.verify_attempts += 1
        db.commit()


def reset_verify_attempts(db: Session, email: str) -> None:
    """Reset verify attempts after successful verification."""
    record = db.query(OtpRateLimit).filter(OtpRateLimit.email == email).first()
    if record:
        record.verify_attempts = 0
        db.commit()


# ── OTP Storage (DiskCache) ──────────────────────────────────────────────────

def store_otp(email: str, otp: str) -> None:
    """Store an OTP in cache with expiration."""
    otp_cache.set(email, otp, expire=app_config.OTP_EXPIRES_MINUTES * 60)


def get_stored_otp(email: str) -> str | None:
    """Retrieve stored OTP from cache."""
    return otp_cache.get(email)


def clear_stored_otp(email: str) -> None:
    """Remove stored OTP from cache."""
    otp_cache.delete(email)


# ── OTP Purpose Token (for password reset flow) ──────────────────────────────
def generate_otp_purpose_token(user_id: int, purpose: str) -> str:
    """Create a short-lived token that authorises a specific action (e.g.
    password reset) after OTP verification."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=10)
    payload = {
        "sub": str(user_id),
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, app_config.JWT_SECRET_KEY, algorithm=app_config.JWT_ALGORITHM)


def verify_otp_purpose_token(token: str) -> dict | None:
    """Decode an OTP purpose token. Returns payload or None."""
    try:
        payload = jwt.decode(token, app_config.JWT_SECRET_KEY, algorithms=[app_config.JWT_ALGORITHM])
        return payload
    except Exception:
        return None
