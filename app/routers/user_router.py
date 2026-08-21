"""User router — /me and /verify-token endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import app_config
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.schemas.user_schema import TokenVerifyResponse, UserProfileResponse

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency: decode JWT and return the authenticated User."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không được cung cấp.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(token, expected_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy tài khoản.",
        )
    return user


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: User = Depends(_get_current_user)):
    """Return the profile of the currently authenticated user."""
    return user


@router.get("/verify-token", response_model=TokenVerifyResponse)
async def verify_token_endpoint(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Lightweight endpoint for internal services to validate a JWT."""
    if not token:
        return TokenVerifyResponse(valid=False)

    payload = verify_token(token, expected_type="access")
    if payload is None:
        return TokenVerifyResponse(valid=False)

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        return TokenVerifyResponse(valid=False)

    return TokenVerifyResponse(
        valid=True,
        user=UserProfileResponse.model_validate(user),
    )
