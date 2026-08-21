"""Master User model — single source of truth for identity across all apps."""

from sqlalchemy import Boolean, Column, DateTime, String, text
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "Master identity table for all applications"}

    id = Column(BIGINT, primary_key=True, autoincrement=True, nullable=False)
    username = Column(String(100), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    # Chỉ hai giá trị hợp lệ:
    #   'admin'    → quản trị viên  (toeicapp_user.role='admin'  | careerpath role_id=2)
    #   'employee' → người dùng thường (mọi giá trị còn lại)
    role = Column(String(50), nullable=False, default="employee", server_default=text("'employee'"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    is_verified = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
