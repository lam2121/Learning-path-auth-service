"""User profile schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class UserProfileResponse(BaseModel):
    id: int
    username: Optional[str] = None
    email: str
    full_name: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "employee"
    role_id: int = 1
    is_active: bool = True
    is_verified: bool = False
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def populate_computed_fields(self) -> "UserProfileResponse":
        if not self.name:
            self.name = self.full_name or self.username or (self.email.split("@")[0] if self.email else "")
        if self.role:
            self.role_id = 2 if str(self.role).strip().lower() in ("admin", "administrator") else 1
        return self

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class TokenVerifyResponse(BaseModel):
    valid: bool
    user: Optional[UserProfileResponse] = None
