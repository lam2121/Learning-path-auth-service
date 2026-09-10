import os

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-pytest")

from app.core.config import app_config

app_config.COOKIE_DOMAIN = ""
app_config.COOKIE_SECURE = False
