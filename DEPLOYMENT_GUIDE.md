# Hướng Dẫn Cài Đặt, Kiểm Tra & Triển Khai Auth Service (Cross-Platform Deployment Guide)

> **Mục tiêu**: Hướng dẫn toàn diện từ khâu **kiểm tra tại Local (hỗ trợ cả Windows & Linux/macOS)** đến **triển khai lên Server Production** (`https://careerpath.example.com`) theo quy trình **Zero-Downtime 3 Giai Đoạn**, đảm bảo không gây gián đoạn cho học viên đang sử dụng hệ thống.

---

## 🗺️ TỔNG QUAN LỘ TRÌNH TRIỂN KHAI

```
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 0: Kiểm tra toàn diện tại Local (Windows / Linux) │
│ • Chạy Pytest suite (toàn bộ test cases)                    │
│ • Smoke test qua cURL hoặc Swagger UI (/docs)               │
│ • Xác nhận dữ liệu và chuẩn hóa Role (admin / employee)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 1: Triển khai Auth Service độc lập lên Server     │
│ (Rủi ro = 0% — các ứng dụng hiện tại không bị ảnh hưởng)     │
│ • Clone repo Git lên server: /var/www/auth-service          │
│ • Cài venv, cấu hình .env (HS256 Secret Key & Redis)        │
│ • Tạo auth_db, chạy Alembic migration & migrate user        │
│ • Thiết lập Systemd service chạy ngầm trên port 8001        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 2: Mở Nginx Reverse Proxy & Tích hợp CareerPath    │
│ • Nginx định tuyến /api/auth/                               │
│ • Tích hợp & kiểm thử toàn bộ luồng CareerPath              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 3: Kích hoạt Single Sign-On (Zero Downtime)       │
│ • Backend verify JWT qua chung JWT_SECRET_KEY (HS256)       │
│ • Frontend chuyển endpoint đăng nhập/đăng ký                │
│ • Kiểm thử SSO liên thông 2 chiều                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 GIAI ĐOẠN 0: Kiểm Tra Tại Local (Máy Dev)

> **Hỗ trợ đầy đủ lệnh cho cả Windows (PowerShell) và Linux / macOS (Bash).**

### 0.1. Cài đặt Môi Trường & Khởi Động Auth Service

#### 👉 Trên Windows (PowerShell):
```powershell
# 1. Di chuyển vào thư mục dự án
cd Learning-path-auth-service

# 2. Tạo và kích hoạt môi trường ảo
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Tạo file .env từ mẫu
Copy-Item .env.example .env

# 5. Khởi động Auth Service (Viết trên 1 dòng duy nhất)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 👉 Trên Linux / macOS (Bash):
```bash
# 1. Di chuyển vào thư mục dự án
cd Learning-path-auth-service

# 2. Tạo và kích hoạt môi trường ảo
python3 -m venv venv
source venv/bin/activate

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Tạo file .env từ mẫu
cp .env.example .env

# 5. Khởi động Auth Service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

### 0.2. Chạy Bộ Kiểm Thử Tự Động (Pytest)

> Mở một cửa sổ Terminal mới (đã kích hoạt `venv`):

#### 👉 Trên Windows (PowerShell):
```powershell
cd Learning-path-auth-service
pytest tests/ -v
# Hoặc chạy trực tiếp: .\venv\Scripts\pytest.exe tests/ -v
```

#### 👉 Trên Linux / macOS (Bash):
```bash
cd Learning-path-auth-service
pytest tests/ -v
# Hoặc chạy trực tiếp: venv/bin/pytest tests/ -v
```

---

### 0.3. Smoke Test Thủ Công

Bạn có thể test trực tiếp qua **Swagger UI tại trình duyệt** hoặc dùng **cURL**:

* 📖 **Swagger UI trực quan**: Mở trình duyệt truy cập [http://localhost:8001/docs](http://localhost:8001/docs)

#### 1. Kiểm tra trạng thái Service:
* **Windows (PowerShell)**:
  ```powershell
  curl.exe -s http://localhost:8001/health
  ```
* **Linux / macOS**:
  ```bash
  curl -s http://localhost:8001/health
  ```
* *Kết quả mong đợi:* `{"status":"ok","service":"auth-service"}`

#### 2. Test Đăng ký tài khoản mới:
* **Windows (PowerShell)**:
  ```powershell
  curl.exe -s -X POST http://localhost:8001/api/auth/register `
    -H "Content-Type: application/json" `
    -d '{\"email\":\"test_dev@example.com\",\"username\":\"test_dev\",\"password\":\"Password123@\",\"full_name\":\"Test Developer\"}'
  ```
* **Linux / macOS**:
  ```bash
  curl -s -X POST http://localhost:8001/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{
      "email": "test_dev@example.com",
      "username": "test_dev",
      "password": "Password123@",
      "full_name": "Test Developer"
    }'
  ```

#### 3. Test Đăng nhập:
* **Windows (PowerShell)**:
  ```powershell
  curl.exe -s -X POST http://localhost:8001/api/auth/login `
    -H "Content-Type: application/json" `
    -d '{\"credential\":\"test_dev@example.com\",\"password\":\"Password123@\"}'
  ```
* **Linux / macOS**:
  ```bash
  curl -s -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "credential": "test_dev@example.com",
      "password": "Password123@"
    }'
  ```

---

### 0.4. Kiểm Tra Dữ Liệu và Role trong `auth_db.users`

> **Yêu cầu bắt buộc**: Toàn bộ tài khoản chỉ được mang 1 trong 2 role: `admin` hoặc `employee`.

---

## 🚀 GIAI ĐOẠN 1: Triển Khai Auth Service Lên Server (Rủi ro = 0%)

> **Mục tiêu**: Đưa Auth Service lên chạy ngầm tại cổng `127.0.0.1:8001` trên Server. Các ứng dụng khác vẫn hoạt động 100% bình thường.

### 1.1. Lấy mã nguồn từ Git lên Server
Đăng nhập SSH vào Server và thực hiện:
```bash
# Thư mục chứa service
sudo mkdir -p /var/www/auth-service
sudo chown -R $USER:$USER /var/www/auth-service

# Clone repository
git clone git@github.com:careerpath-ai/auth-service.git /var/www/auth-service
cd /var/www/auth-service
```

### 1.2. Cài đặt Python Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.3. Thiết lập cấu hình `.env` trên Server
Tạo file `.env` tại `/var/www/auth-service/.env`:
```ini
# ── Database Server ──────────────────────────────────────────
MYSQL_HOST=127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=MatKhauDatabaseServer
MYSQL_DB=auth_db
MYSQL_PORT=3306

# ── Redis ────────────────────────────────────────────────────
REDIS_URL=redis://127.0.0.1:6379/0

# ── JWT HS256 ────────────────────────────────────────────────
JWT_SECRET_KEY=<PASTE_YOUR_GENERATED_64_CHAR_HEX_SECRET_HERE>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=https://careerpath.example.com/auth
JWT_AUDIENCE=toeic,careerpath

# ── OTP Settings ─────────────────────────────────────────────
REQUIRE_REGISTER_OTP=true
OTP_EXPIRES_MINUTES=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_MINUTES=10
OTP_MAX_VERIFY_ATTEMPTS=5

# ── SMTP Email ───────────────────────────────────────────────
EMAIL_SENDER=support@careerpath.io
EMAIL_USERNAME=support@careerpath.io
EMAIL_PASSWORD=your_email_app_password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# ── Cookie SSO Production ────────────────────────────────────
COOKIE_DOMAIN=careerpath.example.com
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

### 1.4. Khởi tạo Database `auth_db` & Chạy Alembic Migration
```bash
# Tạo các bảng users, refresh_tokens, otp_rate_limit qua Alembic
alembic upgrade head
```

### 1.5. Cấu hình Systemd Daemon Service
Tạo file `/etc/systemd/system/auth-service.service`:
```ini
[Unit]
Description=CareerPath Auth Microservice (FastAPI HS256)
After=network.target mysql.service redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/auth-service
EnvironmentFile=/var/www/auth-service/.env
ExecStart=/var/www/auth-service/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Phân quyền và kích hoạt service:
```bash
sudo chown -R www-data:www-data /var/www/auth-service
sudo systemctl daemon-reload
sudo systemctl enable auth-service
sudo systemctl start auth-service
```

---

## 🧪 GIAI ĐOẠN 2: Cấu Hình Nginx & Tích Hợp CareerPath

### 2.1. Cấu hình Nginx Reverse Proxy
Mở file cấu hình Nginx site `careerpath.example.com`:

```nginx
# Điều hướng toàn bộ yêu cầu xác thực sang Auth Service
location /api/auth/ {
    proxy_pass         http://127.0.0.1:8001/api/auth/;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_read_timeout 30s;
    proxy_connect_timeout 5s;
}

# Cấu hình cho Server-Sent Events (SSE) stream (CareerPath)
location /api/onboarding/roadmap/notifications/stream {
    proxy_pass         http://127.0.0.1:8000;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_buffering              off;
    proxy_cache                  off;
    proxy_set_header Connection  '';
    proxy_http_version           1.1;
    chunked_transfer_encoding    off;
    proxy_read_timeout           86400s;
    proxy_send_timeout           86400s;
}
```

Kiểm tra cú pháp và reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 📊 BẢNG ĐỐI CHIẾU CẤU HÌNH LOCAL VS PRODUCTION

| Thuộc tính | Môi Trường Local (Dev - Windows / Linux) | Môi Trường Server (Production - Linux) |
| :--- | :--- | :--- |
| **Domain Host** | `localhost` / `127.0.0.1` | `careerpath.example.com` |
| **MySQL Host** | `localhost:3306` | `127.0.0.1:3306` |
| **Database Name** | `auth_db` | `auth_db` |
| **Redis URL** | `redis://localhost:6379/0` | `redis://127.0.0.1:6379/0` |
| **Cookie Domain** | `localhost` | `careerpath.example.com` |
| **Cookie Secure** | `false` (HTTP) | `true` (HTTPS bắt buộc) |
| **Cookie SameSite** | `lax` | `lax` |
| **Bắt buộc OTP khi ĐK** | `false` (tiện test) | `true` (bảo mật production) |
| **JWT Algorithm** | `HS256` | `HS256` |
| **JWT Secret Key** | Dùng chung trong `.env` | Dùng chung trong `.env` trên Server |
| **JWT Issuer** | `https://careerpath.local/auth` | `https://careerpath.example.com/auth` |
| **Uvicorn Runner** | `--reload --host 0.0.0.0` | `--workers 2 --host 127.0.0.1` qua Systemd |
