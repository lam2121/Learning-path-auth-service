"""Refresh token storage for revocation support."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(BIGINT, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
