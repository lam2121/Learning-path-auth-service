# TMA English Practice — Central Auth Microservice

Dịch vụ xác thực tập trung (**Identity Provider & Single Sign-On**) cho 2 ứng dụng **TOEIC** và **CareerPath**.

---

## 1. Yêu Cầu Hệ Thống (Prerequisites)

* **Python**: 3.10+ (Khuyên dùng Python 3.12)
* **MySQL Server**: 8.0+

---

## 2. Hướng Dẫn Cài Đặt Từ Đầu (Installation)

### Bước 1: Di chuyển vào thư mục dự án
```bash
cd auth-service
```

### Bước 2: Tạo và kích hoạt môi trường ảo (Virtual Environment)
```bash
python3 -m venv venv
source venv/bin/activate
```

### Bước 3: Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình biến môi trường `.env`
Sao chép file mẫu và điền thông tin cấu hình:

```bash
cp .env.example .env
```

Nội dung `.env`:
```ini
# ── Database ──────────────────────────────────────────────
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=auth_db
MYSQL_PORT=3306

# ── JWT HS256 ─────────────────────────────────────────────
JWT_SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=https://english-practice.tma.com.vn/auth
JWT_AUDIENCE=toeic,careerpath

# ── OTP & Rate Limit ──────────────────────────────────────
REQUIRE_REGISTER_OTP=false
OTP_EXPIRES_MINUTES=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_MINUTES=10
OTP_MAX_VERIFY_ATTEMPTS=5

# ── SMTP (Gửi OTP qua Email) ──────────────────────────────
EMAIL_SENDER=training@tma.com.vn
EMAIL_USERNAME=your_email@tma.com.vn
EMAIL_PASSWORD=your_email_password
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587

# ── Cookie (SSO) ──────────────────────────────────────────
COOKIE_DOMAIN=localhost
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

### Bước 6: Khởi tạo Database & Chạy Alembic Migration
```bash
# Tạo database auth_db (nếu chưa có)
python3 -c "
import pymysql, os
conn = pymysql.connect(host='localhost', user='root', password='your_mysql_password', port=3306)
with conn.cursor() as cur:
    cur.execute('CREATE DATABASE IF NOT EXISTS auth_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
conn.close()
print('Database auth_db ready!')
"

# Chạy Alembic migration
alembic upgrade head
```

### Bước 7 (Tùy chọn): Migrate tài khoản từ TOEIC sang Auth DB
Nếu bạn muốn chuyển toàn bộ User hiện có từ Database TOEIC sang Auth Service:
```bash
venv/bin/python3 migrate_toeic_users.py --toeic-db toeic
```

---

## 3. Hướng Dẫn Chạy Service (Run)

### A. Chạy ở chế độ Development (Auto-reload khi sửa code)
* **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
  ```
* **Linux / macOS**:
  ```bash
  source venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
  ```
* Service sẽ chạy tại: `http://localhost:8001` (Swagger UI: `http://localhost:8001/docs`).

### B. Chạy ngầm trong Background (Linux Server)
```bash
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 > auth_service.log 2>&1 &
```
* Xem log: `tail -f auth_service.log`
* Dừng service: `pkill -f "uvicorn app.main:app --port 8001"`

---

## 4. Kiểm Thử Hệ Thống (Testing)

Chạy bộ test suite tự động với `pytest`:
* **Windows (PowerShell)**:
  ```powershell
  pytest tests/ -v
  # hoặc: .\venv\Scripts\pytest.exe tests/ -v
  ```
* **Linux / macOS**:
  ```bash
  pytest tests/ -v
  # hoặc: venv/bin/pytest tests/ -v
  ```

---

## 5. Danh Sách API Endpoints Chính

| Method | Endpoint | Mô tả |
| :--- | :--- | :--- |
| `GET` | `/` | Kiểm tra trạng thái và liên kết tài liệu |
| `GET` | `/health` | Kiểm tra trạng thái hoạt động của Service |
| `GET` | `/.well-known/jwks.json` | Metadata thuật toán JWT (HS256) |
| `POST` | `/api/auth/register` | Đăng ký tài khoản (hỗ trợ trực tiếp hoặc qua OTP) |
| `POST` | `/api/auth/register/otp` | Gửi mã OTP xác nhận đăng ký |
| `POST` | `/api/auth/login` | Đăng nhập (Email/Username) $\rightarrow$ Cấp JWT Token & HttpOnly Cookie |
| `POST` | `/api/auth/refresh-token`| Cấp lại Access Token mới (hỗ trợ đọc từ HttpOnly Cookie) |
| `POST` | `/api/auth/logout` | Đăng xuất (thu hồi Refresh Token trong DB + xóa Cookie) |
| `POST` | `/api/auth/password/otp` | Gửi OTP quên mật khẩu |
| `POST` | `/api/auth/password/otp/verify` | Xác thực OTP đổi mật khẩu |
| `PUT` | `/api/auth/password/reset` | Đặt lại mật khẩu mới |
| `GET` | `/api/auth/me` | Lấy thông tin tài khoản hiện tại |
| `GET` | `/api/auth/verify-token` | Xác thực nhanh Token cho các backend nội bộ |

📖 **Tài liệu Swagger UI tương tác trực quan**: Truy cập [http://localhost:8001/docs](http://localhost:8001/docs).
