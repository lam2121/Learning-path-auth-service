from pathlib import Path
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Central configuration for the Auth Microservice.

    Values are loaded from environment variables and/or a `.env` file located
    at the project root.
    """

    # ── Database ──────────────────────────────────────────────────────────
    MYSQL_HOST: str = "localhost"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "auth_db"
    MYSQL_PORT: int = 3306

    # Connection pool
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    DB_CONNECT_TIMEOUT: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_READ_TIMEOUT: int = 20
    DB_WRITE_TIMEOUT: int = 10

    # ── JWT HS256 ─────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "tma-english-practice-super-secret-jwt-key-2026-xyz789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Issuer / audience embedded in every JWT
    JWT_ISSUER: str = "https://english-practice.tma.com.vn/auth"
    JWT_AUDIENCE: str = "toeic,careerpath"

    # ── OTP ───────────────────────────────────────────────────────────────
    REQUIRE_REGISTER_OTP: bool = False
    OTP_EXPIRES_MINUTES: int = 5
    OTP_MAX_REQUESTS_PER_WINDOW: int = 3
    OTP_RATE_LIMIT_WINDOW_MINUTES: int = 10
    OTP_MAX_VERIFY_ATTEMPTS: int = 5

    # ── SMTP ──────────────────────────────────────────────────────────────
    EMAIL_SENDER: str = ""
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_SMTP_SERVER: str = ""
    EMAIL_SMTP_PORT: int = 465

    # ── Cookie (SSO) ─────────────────────────────────────────────────────
    COOKIE_DOMAIN: str = "localhost"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    class Config:
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        case_sensitive = True
        extra = "allow"


app_config = AppConfig()
