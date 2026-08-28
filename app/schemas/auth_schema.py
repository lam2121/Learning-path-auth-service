"""Pydantic v2 schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class OtpPurpose(str, Enum):
    RESET_PASSWORD = "reset_password"
    VERIFY_ACCOUNT = "verify_account"


class CredentialType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"


class UserRole(str, Enum):
    """Hai vai trò hợp lệ duy nhất trong hệ thống.

    - ``employee`` : người dùng thông thường (học viên TOEIC / nhân viên CareerPath).
    - ``admin``    : quản trị viên có toàn quyền trên cả hai ứng dụng.
    """
    EMPLOYEE = "employee"
    ADMIN = "admin"


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterOtpRequest(BaseModel):
    email: EmailStr
    username: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username must not be empty")
        return v.strip()


class RegisterRequest(BaseModel):
    email: str
    username: Optional[str] = None
    password: str
    full_name: Optional[str] = None
    name: Optional[str] = None
    otp: Optional[str] = None
    role: Optional[str] = UserRole.EMPLOYEE

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = str(v).strip().lower()
        if not v or "@" not in v:
            raise ValueError("Email không hợp lệ.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(str(v).strip()) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return str(v)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: str | None) -> str:
        """Chuẩn hóa role — chỉ chấp nhận 'admin' hoặc 'employee'.

        Mọi giá trị khác (student, teacher, learner, guest, …)
        đều được tự động chuyển về 'employee'.
        """
        if not v:
            return UserRole.EMPLOYEE
        safe = str(v).strip().lower()
        if safe not in (UserRole.ADMIN, UserRole.EMPLOYEE):
            return UserRole.EMPLOYEE
        return safe


class RegisterResponse(BaseModel):
    message: str
    user: "UserResponse"


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    credential: str
    password: str

    @field_validator("credential")
    @classmethod
    def credential_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username or email must be provided")
        return v.strip()


class LoginResponse(BaseModel):
    user: "UserResponse"
    message: str = "Login successful"


# ── Guest Login ───────────────────────────────────────────────────────────────

class GuestLoginRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None


# ── Token ─────────────────────────────────────────────────────────────────────

class TokenRefreshRequest(BaseModel):
    """Optional body; the refresh token is primarily read from the HttpOnly
    cookie, but this allows explicit body-based refresh as well."""
    refresh_token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Password Reset ────────────────────────────────────────────────────────────

class PasswordOtpRequest(BaseModel):
    credential: str
    credential_type: CredentialType = CredentialType.EMAIL
    purpose: OtpPurpose = OtpPurpose.RESET_PASSWORD


class PasswordOtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str
    purpose: OtpPurpose = OtpPurpose.RESET_PASSWORD


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not v or len(v.strip()) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class PasswordResetResponse(BaseModel):
    message: str


class OtpResponse(BaseModel):
    success: bool
    message: str
    expires_in_minutes: Optional[int] = None


class OtpVerifyResponse(BaseModel):
    success: bool
    token: str
    message: str


# ── Shared User Response ─────────────────────────────────────────────────────

class UserResponse(BaseModel):
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
    def populate_computed_fields(self) -> "UserResponse":
        if not self.name:
            self.name = self.full_name or self.username or (self.email.split("@")[0] if self.email else "")
        if self.role:
            self.role_id = 2 if str(self.role).strip().lower() in ("admin", "administrator") else 1
        return self

    class Config:
        from_attributes = True
