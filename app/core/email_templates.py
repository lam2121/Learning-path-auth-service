"""Email HTML / plain-text templates for OTP notifications."""

from __future__ import annotations

from email.message import EmailMessage

from app.core.config import app_config

# ── Subjects ──────────────────────────────────────────────────────────────────

REGISTER_OTP_SUBJECT = "CareerPath — Mã xác nhận đăng ký"
PASSWORD_RESET_SUBJECT = "CareerPath — Đặt lại mật khẩu"

# ── Plain Text Bodies ─────────────────────────────────────────────────────────

REGISTER_OTP_PLAIN = """\
Chào bạn,

Mã OTP để hoàn tất đăng ký tài khoản CareerPath của bạn là: {otp}

Mã này sẽ hết hạn sau {expiry_minutes} phút.

Nếu bạn không yêu cầu đăng ký, vui lòng bỏ qua email này.

Trân trọng,
CareerPath Team
"""

PASSWORD_RESET_PLAIN = """\
Chào bạn,

Mã OTP để đặt lại mật khẩu CareerPath của bạn là: {otp}

Mã này sẽ hết hạn sau {expiry_minutes} phút.

Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.

Trân trọng,
CareerPath Team
"""

# ── HTML Bodies ───────────────────────────────────────────────────────────────

REGISTER_OTP_HTML = """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; text-align: center;">
    <h1 style="color: white; margin: 0;">CareerPath</h1>
    <p style="color: rgba(255,255,255,0.9); margin-top: 8px;">Xác nhận đăng ký tài khoản</p>
  </div>
  <div style="padding: 30px 0;">
    <p>Chào bạn,</p>
    <p>Mã OTP để hoàn tất đăng ký tài khoản của bạn là:</p>
    <div style="background: #f4f4f8; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
      <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #667eea;">{otp}</span>
    </div>
    <p style="color: #666;">Mã này sẽ hết hạn sau <strong>{expiry_minutes} phút</strong>.</p>
    <p style="color: #999; font-size: 13px;">Nếu bạn không yêu cầu đăng ký, vui lòng bỏ qua email này.</p>
  </div>
</body>
</html>
"""

PASSWORD_RESET_HTML = """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; border-radius: 10px; text-align: center;">
    <h1 style="color: white; margin: 0;">CareerPath</h1>
    <p style="color: rgba(255,255,255,0.9); margin-top: 8px;">Đặt lại mật khẩu</p>
  </div>
  <div style="padding: 30px 0;">
    <p>Chào bạn,</p>
    <p>Mã OTP để đặt lại mật khẩu của bạn là:</p>
    <div style="background: #f4f4f8; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
      <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #f5576c;">{otp}</span>
    </div>
    <p style="color: #666;">Mã này sẽ hết hạn sau <strong>{expiry_minutes} phút</strong>.</p>
    <p style="color: #999; font-size: 13px;">Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.</p>
  </div>
</body>
</html>
"""


# ── Builder Functions ─────────────────────────────────────────────────────────

def build_register_otp_email(to_email: str, otp: str, expiry_minutes: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = REGISTER_OTP_SUBJECT
    msg["From"] = f"CareerPath <{app_config.EMAIL_SENDER}>"
    msg["To"] = to_email
    msg.set_content(REGISTER_OTP_PLAIN.format(otp=otp, expiry_minutes=expiry_minutes))
    msg.add_alternative(REGISTER_OTP_HTML.format(otp=otp, expiry_minutes=expiry_minutes), subtype="html")
    return msg


def build_password_reset_email(to_email: str, otp: str, expiry_minutes: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = PASSWORD_RESET_SUBJECT
    msg["From"] = f"CareerPath <{app_config.EMAIL_SENDER}>"
    msg["To"] = to_email
    msg.set_content(PASSWORD_RESET_PLAIN.format(otp=otp, expiry_minutes=expiry_minutes))
    msg.add_alternative(PASSWORD_RESET_HTML.format(otp=otp, expiry_minutes=expiry_minutes), subtype="html")
    return msg
