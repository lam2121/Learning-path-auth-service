"""Automated integration test suite for Auth Microservice."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.otp_rate_limit import OtpRateLimit
from app.services.otp_service import store_otp, get_stored_otp

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Clean test data before each test."""
    db = SessionLocal()
    try:
        db.query(RefreshToken).delete()
        db.query(OtpRateLimit).delete()
        db.query(User).filter(User.email.like("%test%@example.com")).delete()
        db.commit()
    finally:
        db.close()
    yield

def test_guest_login_flow():
    """Test guest login endpoint."""
    res = client.post(
        "/api/auth/guest/login",
        json={"email": "guest_test@example.com", "name": "Guest Tester", "phone": "0123456789"},
    )
    assert res.status_code == 200
    data = res.json()
    assert res.cookies.get("access_token") is not None
    assert res.cookies.get("auth_refresh_token") is not None
    assert data["user"]["email"] == "guest_test@example.com"
    assert data["user"]["role"] == "guest"


def test_registration_and_login_flow():
    """Test complete register with OTP -> login -> /me -> verify-token."""
    email = "register_test@example.com"
    username = "regtestuser"
    password = "StrongPassword123!"

    # 1. Mock store OTP for registration
    store_otp(email, "123456")

    # 2. Register
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "otp": "123456",
            "role": "employee",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["user"]["email"] == email
    assert reg_res.cookies.get("access_token") is None
    assert reg_res.cookies.get("auth_refresh_token") is None
    user_id = reg_data["user"]["id"]

    # 3. Login
    login_res = client.post(
        "/api/auth/login",
        json={"credential": username, "password": password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    access_token = login_res.cookies.get("access_token")
    refresh_token = login_res.cookies.get("auth_refresh_token")
    assert access_token is not None
    assert refresh_token is not None
    assert login_data["user"]["email"] == email

    # 4. Access /me (GET & PATCH)
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["id"] == user_id
    assert me_res.json()["email"] == email
    assert me_res.json()["role_id"] == 1
    assert me_res.json()["name"] is not None

    cookie_me_res = client.get(
        "/api/auth/me",
        cookies={"access_token": access_token},
    )
    assert cookie_me_res.status_code == 200
    assert cookie_me_res.json()["id"] == user_id

    patch_res = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"full_name": "Updated Name", "phone": "0901234567"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Updated Name"
    assert patch_res.json()["name"] == "Updated Name"
    assert patch_res.json()["phone"] == "0901234567"

    cookie_patch_res = client.patch(
        "/api/auth/me",
        cookies={"access_token": access_token},
        json={"full_name": "Cookie Updated Name"},
    )
    assert cookie_patch_res.status_code == 200
    assert cookie_patch_res.json()["full_name"] == "Cookie Updated Name"

    # 5. Access /verify-token
    verify_res = client.get(
        "/api/auth/verify-token",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True
    assert verify_res.json()["user"]["id"] == user_id

    # 6. Refresh Token
    ref_res = client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 200
    new_refresh_token = ref_res.cookies.get("auth_refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != refresh_token

    # 7. Old refresh token should now be invalid (rotation)
    old_ref_res = client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert old_ref_res.status_code == 401

    # 8. Logout
    logout_res = client.post(
        "/api/auth/logout",
        cookies={"auth_refresh_token": new_refresh_token},
    )
    assert logout_res.status_code == 200

    # 9. Refresh after logout should fail
    post_logout_ref = client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": new_refresh_token},
    )
    assert post_logout_ref.status_code == 401


def test_password_reset_flow():
    """Test password reset flow with purpose token."""
    email = "reset_test@example.com"
    username = "resettestuser"
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    # Create user directly
    from app.services.auth_service import create_user
    db = SessionLocal()
    try:
        create_user(db, username=username, email=email, password=old_password)
    finally:
        db.close()

    # Verify old password works
    old_login = client.post("/api/auth/login", json={"credential": username, "password": old_password})
    assert old_login.status_code == 200

    # Mock OTP
    store_otp(email, "888999")

    # Verify OTP — now requires email in the body
    otp_verify_res = client.post(
        "/api/auth/password/otp/verify",
        json={"email": email, "otp": "888999", "purpose": "reset_password"},
    )
    assert otp_verify_res.status_code == 200
    purpose_token = otp_verify_res.json()["token"]

    # Reset Password
    reset_res = client.put(
        "/api/auth/password/reset",
        json={"token": purpose_token, "new_password": new_password},
    )
    assert reset_res.status_code == 200

    # Old password should now fail
    failed_login = client.post("/api/auth/login", json={"credential": username, "password": old_password})
    assert failed_login.status_code == 401

    # New password should succeed
    success_login = client.post("/api/auth/login", json={"credential": username, "password": new_password})
    assert success_login.status_code == 200

    # Test form-urlencoded login (supports traditional HTML forms & legacy React apps)
    form_login = client.post(
        "/api/auth/login",
        data={"username": username, "password": new_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert form_login.status_code == 200
    assert form_login.cookies.get("access_token") is not None
