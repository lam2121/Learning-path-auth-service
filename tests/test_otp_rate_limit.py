"""Tests for OTP Rate Limiting logic."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.otp_rate_limit import OtpRateLimit
from app.models.user import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    try:
        db.query(OtpRateLimit).delete()
        db.query(User).filter(User.email.like("%ratelimit%@example.com")).delete()
        db.commit()
    finally:
        db.close()
    yield


@patch("app.routers.auth_router.send_email_async", new_callable=AsyncMock)
def test_otp_rate_limit_exceeded(mock_send):
    """Verify that requesting OTP more than 3 times in 10 minutes returns 429 Too Many Requests."""
    email = "ratelimit_test@example.com"
    username = "ratelimituser"

    from app.services.auth_service import create_user
    db = SessionLocal()
    try:
        create_user(db, username=username, email=email, password="Password123!")
    finally:
        db.close()

    # Requests 1, 2, 3 should succeed
    res1 = client.post("/api/auth/password/otp", json={"credential": email})
    assert res1.status_code == 200
    res2 = client.post("/api/auth/password/otp", json={"credential": email})
    assert res2.status_code == 200
    res3 = client.post("/api/auth/password/otp", json={"credential": email})
    assert res3.status_code == 200

    # Request 4 MUST return 429
    res4 = client.post("/api/auth/password/otp", json={"credential": email})
    assert res4.status_code == 429
    assert "Quá nhiều yêu cầu OTP" in res4.json()["detail"]
