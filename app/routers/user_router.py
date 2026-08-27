"""User router — /me and /verify-token endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, oauth2_scheme
from app.core.security import verify_token
from app.models.user import User
from app.schemas.user_schema import (
    TokenVerifyResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
)

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserProfileResponse.model_validate(user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    payload: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile fields for the currently authenticated user."""
    updated = False
    new_name = payload.full_name or payload.name
    if new_name is not None:
        user.full_name = new_name.strip()
        updated = True
    if payload.phone is not None:
        user.phone = payload.phone.strip()
        updated = True
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url.strip()
        updated = True

    if updated:
        db.add(user)
        db.commit()
        db.refresh(user)

    return UserProfileResponse.model_validate(user)


@router.get("/verify-token", response_model=TokenVerifyResponse)
@router.post("/verify-token", response_model=TokenVerifyResponse)
async def verify_token_endpoint(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Lightweight endpoint for internal services to validate a JWT."""
    if not token:
        return TokenVerifyResponse(valid=False)

    payload = verify_token(token, expected_type="access")
    if payload is None:
        return TokenVerifyResponse(valid=False)

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        return TokenVerifyResponse(valid=False)

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        return TokenVerifyResponse(valid=False)

    return TokenVerifyResponse(
        valid=True,
        user=UserProfileResponse.model_validate(user),
    )
