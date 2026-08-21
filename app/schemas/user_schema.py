"""User profile schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: int
    username: Optional[str] = None
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "employee"
    is_active: bool = True
    is_verified: bool = False
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenVerifyResponse(BaseModel):
    valid: bool
    user: Optional[UserProfileResponse] = None
