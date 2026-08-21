"""OTP rate-limiting tracker to prevent email spam abuse."""

from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class OtpRateLimit(Base):
    __tablename__ = "otp_rate_limit"

    id = Column(BIGINT, primary_key=True, autoincrement=True, nullable=False)
    email = Column(String(255), nullable=False, index=True)
    request_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    verify_attempts = Column(Integer, nullable=False, default=0, server_default=text("0"))
    window_start = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    last_attempt_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
