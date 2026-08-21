# Quy Trình Kiểm Tra & Triển Khai Chuẩn Xác (Zero-Downtime Deployment Guide)

Tài liệu này hướng dẫn chi tiết quy trình đưa **Central Auth Microservice** lên máy chủ production (`https://english-practice.tma.com.vn`), kết nối đồng bộ 2 ứng dụng **TOEIC** và **CareerPath**, đảm bảo **không gây gián đoạn (Zero Downtime)** cho người dùng đang học.

---

## 🗺️ TỔNG QUAN 3 GIAI ĐOẠN TRIỂN KHAI

```
┌────────────────────────────────┐
│ GIAI ĐOẠN 1: Chuẩn bị Server   │ ──► Deploy Auth Service độc lập lên cổng 8001
│ (Rủi ro = 0%)                  │     Khởi tạo auth_db & migrate tài khoản TOEIC
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│ GIAI ĐOẠN 2: Test CareerPath   │ ──► Mở đường Nginx proxy /api/auth/
│ (Rủi ro = 0% với TOEIC)        │     Test toàn diện trên app CareerPath
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│ GIAI ĐOẠN 3: Chuyển đổi TOEIC  │ ──► Dual-token verification (nhận cả token cũ & mới)
│ (Zero Downtime cho TOEIC)      │     Kích hoạt Single Sign-On (SSO) toàn hệ thống
└────────────────────────────────┘
```

---

## 🚀 GIAI ĐOẠN 1: Triển Khai Auth Service Độc Lập Lên Server (Rủi ro = 0%)

> *Mục tiêu: Auth Service chạy ngầm trên cổng `127.0.0.1:8001` của Server. Ở giai đoạn này, TOEIC và CareerPath vẫn chạy 100% bình thường, chưa hề bị tác động.*

### 1.1. Copy mã nguồn `auth-service` lên Server
Copy thư mục `auth-service` lên server (ví dụ tại `/var/www/auth-service` hoặc thư mục dự án):
```bash
# Trên server:
mkdir -p /var/www/auth-service
cd /var/www/auth-service
```

### 1.2. Cài đặt môi trường ảo & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.3. Cấu hình file `.env` trên Server
Tạo file `/var/www/auth-service/.env`:
```ini
# Database Server
MYSQL_HOST=127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=MatKhauDatabaseServer
MYSQL_DB=auth_db
MYSQL_PORT=3306

# JWT RS256
RSA_PRIVATE_KEY_PATH=keys/private_key.pem
RSA_PUBLIC_KEY_PATH=keys/public_key.pem
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=https://english-practice.tma.com.vn/auth
JWT_AUDIENCE=toeic,careerpath

# OTP Settings
REQUIRE_REGISTER_OTP=false
OTP_EXPIRES_MINUTES=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_MINUTES=10
OTP_MAX_VERIFY_ATTEMPTS=5

# SMTP Email
EMAIL_SENDER=training@tma.com.vn
EMAIL_USERNAME=ltuan@tma.com.vn
EMAIL_PASSWORD=EDZFBDUTRUIWXLDU
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587

# Cookie SSO Production
COOKIE_DOMAIN=english-practice.tma.com.vn
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

### 1.4. Tạo Cặp Khóa RS256
```bash
mkdir -p keys
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
chmod 600 keys/private_key.pem
```

### 1.5. Tạo Database & Áp dụng Alembic Migration
```bash
# 1. Tạo Database
python3 -c "
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='root', password='MatKhauDatabaseServer', port=3306)
with conn.cursor() as cur:
    cur.execute('CREATE DATABASE IF NOT EXISTS auth_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
conn.close()
print('Database auth_db created!')
"

# 2. Chạy Alembic Migration
alembic upgrade head
```

### 1.6. Chuyển đổi dữ liệu User cũ từ TOEIC sang `auth_db`
```bash
venv/bin/python3 migrate_toeic_users.py --toeic-db toeic_learningpath
```
*(Toàn bộ tài khoản cũ sẽ được copy sang `auth_db.users` với mật khẩu Bcrypt giữ nguyên 100%)*.

### 1.7. Tạo Service chạy tự động (Systemd)
Tạo file `/etc/systemd/system/auth-service.service`:
```ini
[Unit]
Description=Central Auth Microservice
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/var/www/auth-service
ExecStart=/var/www/auth-service/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Kích hoạt và chạy service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable auth-service
sudo systemctl start auth-service
```

### ✅ Checklist kiểm tra Giai đoạn 1:
```bash
# 1. Kiểm tra trạng thái service:
sudo systemctl status auth-service

# 2. Kiểm tra API nội bộ:
curl http://127.0.0.1:8001/health
# Output: {"status":"ok","service":"auth-service"}

# 3. Kiểm tra JWKS:
curl http://127.0.0.1:8001/.well-known/jwks.json

# 4. Chạy test suite:
venv/bin/pytest tests/ -v
# Output: 6 passed in 5s
```

---

## 🧪 GIAI ĐOẠN 2: Bật Nginx & Tích Hợp Thử Nghiệm CareerPath

> *Mục tiêu: Cho phép Nginx điều hướng các request xác thực sang Auth Service. Chuyển đổi CareerPath sang dùng Auth Service trước để kiểm tra toàn bộ luồng mà không lo ảnh hưởng TOEIC.*

### 2.1. Cấu hình Nginx Reverse Proxy
Mở file cấu hình Nginx của site `english-practice.tma.com.vn` (ví dụ `/etc/nginx/sites-enabled/...`):

Thêm 2 block sau vào trong block `server { ... }`:
```nginx
# 1. Chuyển hướng request Auth
location /api/auth/ {
    proxy_pass http://127.0.0.1:8001/api/auth/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# 2. Expose JWKS Endpoint
location /.well-known/jwks.json {
    proxy_pass http://127.0.0.1:8001/.well-known/jwks.json;
}
```

Kiểm tra và reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 2.2. Kiểm tra từ bên ngoài trình duyệt
Mở trình duyệt bất kỳ truy cập:
* `https://english-practice.tma.com.vn/api/auth/health` $\rightarrow$ Thấy `{"status":"ok"}`.
* `https://english-practice.tma.com.vn/.well-known/jwks.json` $\rightarrow$ Thấy JSON Public Key.

### 2.3. Cập nhật & Deploy CareerPath
1. **CareerPath Backend (`careerpath-fastapi`)**:
   * File `.env` trỏ: `AUTH_JWKS_URL=http://127.0.0.1:8001/.well-known/jwks.json`.
   * Restart backend CareerPath.
2. **CareerPath Frontend (`careerpath-react-ts-vite`)**:
   * File `.env.production`: `VITE_AUTH_API_URL=/api/auth`.
   * Build và deploy bundle: `npm run build`.

### ✅ Checklist kiểm tra Giai đoạn 2:
1. Mở trang: `https://english-practice.tma.com.vn/careerpath/login`.
2. Dùng một tài khoản **đã có sẵn từ TOEIC** đăng nhập vào CareerPath $\rightarrow$ Đăng nhập thành công, tự tạo Profile CareerPath (Auto-provisioning).
3. Thử đăng ký một tài khoản mới tinh trên CareerPath $\rightarrow$ Đăng ký và đăng nhập thành công.
4. Thử làm bài Quiz / Onboarding $\rightarrow$ Dữ liệu lộ trình lưu đúng vào `toeic_learningpath` DB.

---

## 🔄 GIAI ĐOẠN 3: Chuyển Đổi TOEIC An Toàn (Zero Downtime)

> *Mục tiêu: Đưa TOEIC sang dùng Auth Service mà các bạn đang học/làm bài thi trên TOEIC không bị văng ra giữa chừng.*

### 3.1. Cập nhật TOEIC Backend trước (Cơ chế Dual-Verification)
Cập nhật file `jwt_helper.py` và `auth_dependencies.py` trên backend TOEIC:
* **Ưu tiên 1**: Verify chữ ký RS256 token mới qua JWKS (`http://127.0.0.1:8001/.well-known/jwks.json`).
* **Ưu tiên 2 (Fallback)**: Nếu token là định dạng HS256 cũ mà người dùng đang giữ từ trước $\rightarrow$ Tiếp tục chấp nhận hợp lệ.
* Restart TOEIC Backend.

### 3.2. Cập nhật TOEIC Frontend
Cập nhật file `authService.ts` trên TOEIC Frontend:
* Các request đăng nhập/đăng ký trỏ sang `/api/auth/login`, `/api/auth/register`.
* Build và deploy frontend TOEIC.

### 3.3. Kiểm tra tính năng Single Sign-On (SSO) giữa 2 App:
1. Mở trình duyệt vào **TOEIC**: `https://english-practice.tma.com.vn/login` $\rightarrow$ Đăng nhập.
2. Mở tab mới truy cập **CareerPath**: `https://english-practice.tma.com.vn/careerpath/` $\rightarrow$ **Tự động nhận diện tài khoản, không cần đăng nhập lại**.
3. Bấm **Đăng xuất (Logout)** ở một bên $\rightarrow$ Cả 2 app tự động hủy phiên an toàn.

---

## 🛡️ KẾ HOẠCH HOÀN NGUYÊN (ROLLBACK PLAN)

Nếu trong quá trình triển khai có sự cố bất ngờ:

1. **Khôi phục Nginx về trạng thái cũ**:
   Xóa/Comment 2 block `location /api/auth/` và `location /.well-known/jwks.json` trong file Nginx $\rightarrow$ `sudo systemctl reload nginx`.
2. **Khôi phục Frontend/Backend**:
   Quay lại phiên bản build cũ của frontend và backend.
3. ⏱️ **Thời gian hoàn nguyên**: Chưa đầy **1 phút**, hệ thống quay về trạng thái ban đầu an toàn 100%.
