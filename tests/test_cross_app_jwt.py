"""Test verifying tokens using shared secret as CareerPath/TOEIC resource servers will do."""

from fastapi.testclient import TestClient
from jose import jwt
from app.main import app
from app.core.config import app_config
from app.core.database import SessionLocal
from app.models.user import User
from app.services.auth_service import create_user

client = TestClient(app)


def test_cross_app_hs256_verification():
    """Simulate CareerPath/TOEIC backend verifying an HS256 JWT issued by Auth Service."""
    # 1. Create user and login via Auth Service
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == "crossapp@example.com").delete()
        db.commit()
        create_user(db, username="crossappuser", email="crossapp@example.com", password="Password123!", role="employee")
    finally:
        db.close()

    login_res = client.post("/api/auth/login", json={"credential": "crossappuser", "password": "Password123!"})
    assert login_res.status_code == 200
    access_token = login_res.cookies.get("access_token")
    assert access_token is not None

    # 2. CareerPath / TOEIC decodes JWT using the shared SECRET_KEY with HS256
    decoded = jwt.decode(
        access_token,
        app_config.JWT_SECRET_KEY,
        algorithms=["HS256"],
        issuer=app_config.JWT_ISSUER,
        options={"verify_aud": False},
    )

    # 3. Assert token claims are standard and complete
    assert decoded["email"] == "crossapp@example.com"
    assert decoded["role"] == "employee"
    assert decoded["token_type"] == "access"
    assert "toeic" in decoded["aud"]
    assert "careerpath" in decoded["aud"]
    assert decoded["iss"] == app_config.JWT_ISSUER
