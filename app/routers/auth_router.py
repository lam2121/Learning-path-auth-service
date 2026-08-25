"""Auth router — register, login, refresh, logout, password reset, guest login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import app_config
from app.core.database import get_db
from app.core.email_templates import build_password_reset_email, build_register_otp_email
from app.core.smtp import send_email_async
from app.schemas.auth_schema import (
    GuestLoginRequest,
    LoginRequest,
    LoginResponse,
    OtpResponse,
    OtpVerifyResponse,
    PasswordOtpRequest,
    PasswordOtpVerifyRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterOtpRequest,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_email_or_username,
    get_user_by_id,
    get_user_by_username,
    upsert_guest_user,
)
from app.services.otp_service import (
    check_otp_rate_limit,
    check_verify_attempts,
    clear_stored_otp,
    generate_otp,
    generate_otp_purpose_token,
    get_stored_otp,
    increment_verify_attempts,
    reset_verify_attempts,
    store_otp,
    verify_otp_purpose_token,
)
from app.services.token_service import (
    issue_tokens,
    refresh_access_token,
    revoke_refresh_token,
)
from app.core.security import hash_password

router = APIRouter()

REFRESH_COOKIE_NAME = "auth_refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the HttpOnly refresh-token cookie on the response."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=app_config.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=app_config.COOKIE_SECURE,
        samesite=app_config.COOKIE_SAMESITE,
        domain=app_config.COOKIE_DOMAIN if app_config.COOKIE_DOMAIN != "localhost" else None,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Delete the refresh-token cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=app_config.COOKIE_SECURE,
        samesite=app_config.COOKIE_SAMESITE,
        domain=app_config.COOKIE_DOMAIN if app_config.COOKIE_DOMAIN != "localhost" else None,
        path="/",
    )


# ── Register OTP ──────────────────────────────────────────────────────────────

@router.post("/register/otp", response_model=OtpResponse)
async def request_register_otp(req: RegisterOtpRequest, db: Session = Depends(get_db)):
    # Rate limit check
    check_otp_rate_limit(db, req.email)

    # Check if email or username already taken
    email_clean = req.email.strip()
    username_clean = req.username.strip()

    if get_user_by_email(db, email_clean):
        raise HTTPException(status_code=400, detail="Email đã được đăng ký.")
    if get_user_by_username(db, username_clean):
        raise HTTPException(status_code=400, detail="Username đã được sử dụng. Vui lòng chọn username khác.")

    # Generate and store OTP
    otp = generate_otp()
    store_otp(email_clean, otp)

    # Send email
    try:
        msg = build_register_otp_email(email_clean, otp, str(app_config.OTP_EXPIRES_MINUTES))
        await send_email_async(msg)
    except Exception:
        clear_stored_otp(email_clean)
        raise HTTPException(status_code=400, detail="Không thể gửi email OTP. Vui lòng thử lại.")

    return OtpResponse(
        success=True,
        message="Mã OTP đã được gửi tới email của bạn.",
        expires_in_minutes=app_config.OTP_EXPIRES_MINUTES,
    )


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email_clean = req.email.strip()
    username_clean = req.username.strip()

    # Verify OTP if provided or required
    if req.otp:
        cached_otp = get_stored_otp(email_clean)
        if not cached_otp:
            raise HTTPException(status_code=400, detail="OTP đã hết hạn hoặc chưa được yêu cầu.")
        if cached_otp != req.otp:
            raise HTTPException(status_code=400, detail="Mã OTP không chính xác.")
        clear_stored_otp(email_clean)
    elif app_config.REQUIRE_REGISTER_OTP:
        raise HTTPException(status_code=400, detail="Vui lòng yêu cầu mã OTP trước khi đăng ký.")

    # Check duplicate
    if get_user_by_email(db, email_clean):
        raise HTTPException(status_code=400, detail="Email đã được đăng ký.")
    if get_user_by_username(db, username_clean):
        raise HTTPException(status_code=400, detail="Username đã được sử dụng. Vui lòng chọn username khác.")

    # Create user
    user = create_user(
        db,
        username=username_clean,
        email=email_clean,
        password=req.password,
        full_name=req.full_name.strip() if req.full_name else None,
        role=req.role,
    )

    # Issue tokens
    tokens = issue_tokens(user, db)
    _set_refresh_cookie(response, tokens["refresh_token"])

    user_resp = UserResponse.model_validate(user)
    return RegisterResponse(message="Đăng ký thành công!", user=user_resp)


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
    credential = None
    password = None

    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                credential = (
                    body.get("credential")
                    or body.get("username")
                    or body.get("email")
                    or body.get("identifier")
                )
                password = body.get("password")
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form = await request.form()
            credential = (
                form.get("credential")
                or form.get("username")
                or form.get("email")
                or form.get("identifier")
            )
            password = form.get("password")
        except Exception:
            pass
    else:
        # Fallback: try reading JSON first, then Form
        try:
            body = await request.json()
            if isinstance(body, dict):
                credential = (
                    body.get("credential")
                    or body.get("username")
                    or body.get("email")
                    or body.get("identifier")
                )
                password = body.get("password")
        except Exception:
            try:
                form = await request.form()
                credential = (
                    form.get("credential")
                    or form.get("username")
                    or form.get("email")
                    or form.get("identifier")
                )
                password = form.get("password")
            except Exception:
                pass

    if not credential or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vui lòng cung cấp đầy đủ tên đăng nhập (username/email) và mật khẩu.",
        )

    user = authenticate_user(db, str(credential).strip(), str(password))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
        )

    device_info = request.headers.get("User-Agent", "unknown")
    tokens = issue_tokens(user, db, device_info=device_info)
    _set_refresh_cookie(response, tokens["refresh_token"])

    user_resp = UserResponse.model_validate(user)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user=user_resp,
    )


# ── Refresh Token ─────────────────────────────────────────────────────────────

@router.post("/refresh-token")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    # Read from body if explicitly provided, fallback to HttpOnly cookie
    raw_token = None
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                raw_token = body.get("refresh_token")
        except Exception:
            pass

    if not raw_token:
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not raw_token:
        raise HTTPException(status_code=401, detail="Refresh token không tìm thấy.")

    result = refresh_access_token(raw_token, db)
    if result is None:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ hoặc đã bị thu hồi.")

    _set_refresh_cookie(response, result["refresh_token"])
    return result


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        revoke_refresh_token(raw_token, db)
    _clear_refresh_cookie(response)
    return {"success": True, "message": "Đăng xuất thành công."}


# ── Password OTP ──────────────────────────────────────────────────────────────

@router.post("/password/otp", response_model=OtpResponse)
async def request_password_otp(req: PasswordOtpRequest, db: Session = Depends(get_db)):
    check_otp_rate_limit(db, req.credential)

    user = get_user_by_email_or_username(db, req.credential)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    otp = generate_otp()
    store_otp(user.email, otp)

    try:
        msg = build_password_reset_email(user.email, otp, str(app_config.OTP_EXPIRES_MINUTES))
        await send_email_async(msg)
    except Exception:
        clear_stored_otp(user.email)
        raise HTTPException(status_code=500, detail="Không thể gửi email OTP.")

    return OtpResponse(
        success=True,
        message=f"Mã OTP đã được gửi tới email của bạn.",
        expires_in_minutes=app_config.OTP_EXPIRES_MINUTES,
    )


# ── Password OTP Verify ──────────────────────────────────────────────────────

@router.post("/password/otp/verify", response_model=OtpVerifyResponse)
async def verify_password_otp(req: PasswordOtpVerifyRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()

    check_verify_attempts(db, email_clean)

    # Direct lookup by email — no brute-search needed
    stored = get_stored_otp(email_clean)
    if stored is None or stored != req.otp:
        increment_verify_attempts(db, email_clean)
        raise HTTPException(status_code=400, detail="Mã OTP không hợp lệ hoặc đã hết hạn.")

    user = get_user_by_email(db, email_clean)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    # OTP is valid — clear it and issue a purpose token
    clear_stored_otp(email_clean)
    reset_verify_attempts(db, email_clean)

    purpose_token = generate_otp_purpose_token(user.id, req.purpose.value)
    return OtpVerifyResponse(success=True, token=purpose_token, message="OTP xác thực thành công.")


# ── Password Reset ────────────────────────────────────────────────────────────

@router.put("/password/reset", response_model=PasswordResetResponse)
async def reset_password(req: PasswordResetRequest, db: Session = Depends(get_db)):
    payload = verify_otp_purpose_token(req.token)
    if not payload or payload.get("purpose") != "reset_password":
        raise HTTPException(status_code=400, detail="Token đặt lại mật khẩu không hợp lệ.")

    user = get_user_by_id(db, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    user.hashed_password = hash_password(req.new_password)
    db.commit()

    return PasswordResetResponse(message="Mật khẩu đã được đặt lại thành công.")


# ── Guest Login ───────────────────────────────────────────────────────────────

@router.post("/guest/login", response_model=LoginResponse)
async def guest_login(req: GuestLoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = upsert_guest_user(db, email=req.email, name=req.name, phone=req.phone)

    device_info = request.headers.get("User-Agent", "unknown")
    tokens = issue_tokens(user, db, device_info=device_info)
    _set_refresh_cookie(response, tokens["refresh_token"])

    user_resp = UserResponse.model_validate(user)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user=user_resp,
    )
