"""Token service — create / verify JWT, manage refresh token revocation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import app_config
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


def issue_tokens(user: User, db: Session, device_info: str | None = None) -> dict:
    """Issue a fresh access + refresh token pair and persist the refresh token hash.

    Returns ``{"access_token": ..., "refresh_token": ..., "token_type": "bearer"}``.
    """
    token_data = {
        "sub": str(user.id),
        "user_id": user.id,
        "email": user.email,
        "name": user.full_name or user.username or "",
        "role": user.role,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Persist refresh token hash for revocation
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        device_info=device_info,
        expires_at=datetime.now(timezone.utc) + timedelta(days=app_config.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(db_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token(raw_refresh_token: str, db: Session) -> dict | None:
    """Validate a refresh token, revoke the old one, and issue a fresh pair.

    Returns the new token dict, or ``None`` if the refresh token is invalid /
    revoked / expired.
    """
    payload = verify_token(raw_refresh_token, expected_type="refresh")
    if payload is None:
        return None

    token_hash = hash_refresh_token(raw_refresh_token)
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False)
        .with_for_update()
        .first()
    )
    if stored is None:
        return None

    # Revoke old token
    stored.revoked = True
    db.commit()

    # Fetch user
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        return None

    # Issue brand new pair (token rotation)
    return issue_tokens(user, db, device_info=stored.device_info)


def revoke_refresh_token(raw_refresh_token: str, db: Session) -> bool:
    """Revoke a specific refresh token (logout).  Returns True if revoked."""
    token_hash = hash_refresh_token(raw_refresh_token)
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False)
        .with_for_update()
        .first()
    )
    if stored is None:
        return False
    stored.revoked = True
    db.commit()
    return True


def revoke_all_user_tokens(user_id: int, db: Session) -> int:
    """Revoke ALL refresh tokens for a user (force logout everywhere)."""
    count = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .update({"revoked": True})
    )
    db.commit()
    return count
