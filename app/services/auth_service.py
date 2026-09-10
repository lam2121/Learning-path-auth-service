"""Core authentication business logic."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def authenticate_user(db: Session, credential: str, password: str) -> User | None:
    """Authenticate by email or username.  Returns the User or None."""
    user = (
        db.query(User)
        .filter((User.email == credential) | (User.username == credential))
        .first()
    )
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.",
        )
    return user


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    role: str = "employee",
    full_name: str | None = None,
    phone: str | None = None,
    is_verified: bool = True,
) -> User:
    """Create a new master user."""
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=role,
        is_verified=is_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.strip()).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username.strip()).first()


def get_user_by_email_or_username(db: Session, credential: str) -> User | None:
    cred = credential.strip()
    return (
        db.query(User)
        .filter((User.email == cred) | (User.username == cred))
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def upsert_guest_user(
    db: Session, *, email: str, name: str | None = None, phone: str | None = None
) -> User:
    """Find or create a guest user account."""
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        if user.role != "guest":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email đã được đăng ký tài khoản chính thức. Vui lòng đăng nhập bằng mật khẩu.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.",
            )
        return user

    user = User(
        username=email,
        email=email,
        hashed_password="",  # Guest users have no password
        full_name=name,
        phone=phone,
        role="guest",
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
