"""Test verifying tokens using JWKS public key as CareerPath/TOEIC resource servers will do."""

from fastapi.testclient import TestClient
from jose import jwt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.services.auth_service import create_user

client = TestClient(app)


def test_cross_app_jwks_verification():
    """Simulate CareerPath backend verifying a JWT issued by Auth Service using JWKS."""
    # 1. Create user and login via Auth Service
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == "crossapp@example.com").delete()
        db.commit()
        create_user(db, username="crossappuser", email="crossapp@example.com", password="Password123!", role="learner")
    finally:
        db.close()

    login_res = client.post("/api/auth/login", json={"credential": "crossappuser", "password": "Password123!"})
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]

    # 2. CareerPath fetches JWKS
    jwks_res = client.get("/.well-known/jwks.json")
    assert jwks_res.status_code == 200
    jwks_data = jwks_res.json()
    assert "keys" in jwks_data
    key_info = jwks_data["keys"][0]

    # 3. CareerPath decodes JWT using the public key from JWKS
    # (python-jose supports decoding with dict containing JWK or PEM)
    from jose import jwk
    public_key = jwk.construct(key_info)

    decoded = jwt.decode(
        access_token,
        public_key.to_pem().decode(),
        algorithms=["RS256"],
        issuer="https://english-practice.tma.com.vn/auth",
        options={"verify_aud": False},
    )

    # 4. Assert token claims are standard and complete
    assert decoded["email"] == "crossapp@example.com"
    assert decoded["role"] == "learner"
    assert decoded["token_type"] == "access"
    assert "toeic" in decoded["aud"]
    assert "careerpath" in decoded["aud"]
    assert decoded["iss"] == "https://english-practice.tma.com.vn/auth"
