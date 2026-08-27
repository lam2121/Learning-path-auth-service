# Hướng Dẫn Cài Đặt, Kiểm Tra & Triển Khai Auth Service (Cross-Platform Deployment Guide)

> **Mục tiêu**: Hướng dẫn toàn diện từ khâu **kiểm tra tại Local (hỗ trợ cả Windows & Linux/macOS)** đến **triển khai lên Server Production** (`https://english-practice.tma.com.vn`) theo quy trình **Zero-Downtime 3 Giai Đoạn**, đảm bảo không gây gián đoạn cho học viên đang sử dụng hệ thống.

---

## 🗺️ TỔNG QUAN LỘ TRÌNH TRIỂN KHAI

```
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 0: Kiểm tra toàn diện tại Local (Windows / Linux) │
│ • Chạy Pytest suite (6/6 test cases)                        │
│ • Smoke test qua cURL hoặc Swagger UI (/docs)               │
│ • Xác nhận dữ liệu và chuẩn hóa Role (admin / employee)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 1: Triển khai Auth Service độc lập lên Server     │
│ (Rủi ro = 0% — TOEIC & CareerPath hiện tại không bị ảnh hưởng)│
│ • Clone repo Git lên server: /var/www/auth-service          │
│ • Cài venv, cấu hình .env (HS256 Secret Key)                │
│ • Tạo auth_db, chạy Alembic migration & migrate user cũ     │
│ • Thiết lập Systemd service chạy ngầm trên port 8001        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 2: Mở Nginx Reverse Proxy & Tích hợp CareerPath    │
│ (Rủi ro = 0% đối với TOEIC)                                 │
│ • Nginx định tuyến /api/auth/                               │
│ • Tích hợp & kiểm thử toàn bộ luồng CareerPath              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 3: Chuyển đổi TOEIC & Kích hoạt Single Sign-On    │
│ (Zero-Downtime — Học viên đang làm bài không bị văng ra)    │
│ • Backend TOEIC verify JWT qua chung JWT_SECRET_KEY (HS256) │
│ • Frontend TOEIC chuyển endpoint đăng nhập/đăng ký          │
│ • Kiểm thử SSO liên thông 2 chiều TOEIC ↔ CareerPath        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 GIAI ĐOẠN 0: Kiểm Tra Tại Local (Máy Dev)

> **Hỗ trợ đầy đủ lệnh cho cả Windows (PowerShell) và Linux / macOS (Bash).**

### 0.1. Cài đặt Môi Trường & Khởi Động Auth Service

#### 👉 Trên Windows (PowerShell):
```powershell
# 1. Di chuyển vào thư mục dự án
cd auth-service

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
cd auth-service

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
cd auth-service
pytest tests/ -v
# Hoặc chạy trực tiếp: .\venv\Scripts\pytest.exe tests/ -v
```

#### 👉 Trên Linux / macOS (Bash):
```bash
cd auth-service
pytest tests/ -v
# Hoặc chạy trực tiếp: venv/bin/pytest tests/ -v
```

**Kết quả yêu cầu đạt 100% (6/6 pass):**
```
tests/test_auth_endpoints.py::test_jwks_endpoint PASSED                  [ 16%]
tests/test_auth_endpoints.py::test_guest_login_flow PASSED               [ 33%]
tests/test_auth_endpoints.py::test_registration_and_login_flow PASSED    [ 50%]
tests/test_auth_endpoints.py::test_password_reset_flow PASSED            [ 66%]
tests/test_cross_app_jwt.py::test_cross_app_hs256_verification PASSED    [ 83%]
tests/test_otp_rate_limit.py::test_otp_rate_limit_exceeded PASSED        [100%]
======================== 6 passed in Xs ========================
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
    -d '{\"email\":\"test_dev@tma.com.vn\",\"username\":\"test_dev\",\"password\":\"Password123@\",\"full_name\":\"Test Developer\"}'
  ```
* **Linux / macOS**:
  ```bash
  curl -s -X POST http://localhost:8001/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{
      "email": "test_dev@tma.com.vn",
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
    -d '{\"credential\":\"test_dev@tma.com.vn\",\"password\":\"Password123@\"}'
  ```
* **Linux / macOS**:
  ```bash
  curl -s -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "credential": "test_dev@tma.com.vn",
      "password": "Password123@"
    }'
  ```

---

### 0.4. Kiểm Tra Dữ Liệu và Role trong `auth_db.users`

#### 👉 Trên Windows (PowerShell):
```powershell
python -c "
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='123456x@X', port=3306)
with conn.cursor() as cur:
    cur.execute('SELECT role, COUNT(*) FROM auth_db.users GROUP BY role ORDER BY role;')
    print('Thong ke Role trong auth_db.users:')
    for r in cur.fetchall():
        print(f'  Role: {r[0]:<12} So luong: {r[1]}')
conn.close()
"
```

#### 👉 Trên Linux / macOS (Bash):
```bash
python3 -c "
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='123456x@X', port=3306)
with conn.cursor() as cur:
    cur.execute('SELECT role, COUNT(*) FROM auth_db.users GROUP BY role ORDER BY role;')
    print('Thống kê Role trong auth_db.users:')
    for r in cur.fetchall():
        print(f'  Role: {r[0]:<12} Số lượng: {r[1]}')
conn.close()
"
```
> **Yêu cầu bắt buộc**: Toàn bộ tài khoản chỉ được mang 1 trong 2 role: `admin` hoặc `employee`.

---

## 🚀 GIAI ĐOẠN 1: Triển Khai Auth Service Lên Server (Rủi ro = 0%)

> **Mục tiêu**: Đưa Auth Service lên chạy ngầm tại cổng `127.0.0.1:8001` trên Server. Hai ứng dụng TOEIC và CareerPath vẫn hoạt động 100% bình thường.

### 1.1. Lấy mã nguồn từ Git lên Server
Đăng nhập SSH vào Server và thực hiện:
```bash
# Thư mục chứa service (ví dụ /var/www/auth-service)
sudo mkdir -p /var/www/auth-service
sudo chown -R $USER:$USER /var/www/auth-service

# Clone repository từ Git TMA
git clone git@gitsdc.tma.com.vn:careerpath-english/auth-service.git /var/www/auth-service
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

# ── JWT HS256 ────────────────────────────────────────────────
JWT_SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=https://english-practice.tma.com.vn/auth
JWT_AUDIENCE=toeic,careerpath

# ── OTP Settings ─────────────────────────────────────────────
REQUIRE_REGISTER_OTP=true
OTP_EXPIRES_MINUTES=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_MINUTES=10
OTP_MAX_VERIFY_ATTEMPTS=5

# ── SMTP Email ───────────────────────────────────────────────
EMAIL_SENDER=training@tma.com.vn
EMAIL_USERNAME=ltuan@tma.com.vn
EMAIL_PASSWORD=EDZFBDUTRUIWXLDU
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587

# ── Cookie SSO Production ────────────────────────────────────
COOKIE_DOMAIN=english-practice.tma.com.vn
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

### 1.4. Khởi tạo Database `auth_db` & Chạy Alembic Migration
```bash
# 1. Tạo database auth_db trên MySQL Server
python3 create_db.py

# 2. Tạo các bảng users, refresh_tokens, otp_rate_limit qua Alembic
alembic upgrade head
```

### 1.5. Đồng bộ dữ liệu User từ TOEIC & CareerPath sang `auth_db`
Chạy script migration để chuyển toàn bộ user hiện tại vào Central Auth DB (mật khẩu Bcrypt được giữ nguyên 100%):
```bash
# Migrate từ database TOEIC
python3 migrate_toeic_users.py --toeic-db toeic

# Migrate từ database CareerPath (nếu có)
python3 migrate_toeic_users.py --toeic-db toeic_learningpath
```

### 1.6. Cấu hình Systemd Daemon Service
Tạo file `/etc/systemd/system/auth-service.service`:
```ini
[Unit]
Description=Central Auth Microservice (FastAPI HS256)
After=network.target mysql.service

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

### ✅ Checklist nghiệm thu Giai đoạn 1:
```bash
# 1. Trạng thái service đang active
sudo systemctl status auth-service

# 2. Kiểm tra endpoint nội bộ
curl -s http://127.0.0.1:8001/health
# {"status":"ok","service":"auth-service"}

# 3. Chạy test suite trực tiếp trên server
cd /var/www/auth-service && pytest tests/ -v
```

---

## 🧪 GIAI ĐOẠN 2: Cấu Hình Nginx & Tích Hợp CareerPath

> **Mục tiêu**: Mở đường cho Nginx reverse proxy vào Auth Service và kết nối CareerPath. Giai đoạn này hoàn toàn độc lập, không tác động đến người dùng TOEIC.

### 2.1. Cấu hình Nginx Reverse Proxy
Mở file cấu hình Nginx site `english-practice.tma.com.vn` (thường ở `/etc/nginx/sites-available/` hoặc `/etc/nginx/conf.d/`):

Thêm block sau vào bên trong block `server { ... }` (phần SSL / HTTPS):
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
```

Kiểm tra cú pháp và reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 2.2. Kiểm tra từ Internet / Trình duyệt bên ngoài
Truy cập qua HTTPS công khai:
* `https://english-practice.tma.com.vn/api/auth/health` $\rightarrow$ Thấy `{"status":"ok"}`.

### 2.3. Cập nhật CareerPath Backend (`careerpath-fastapi`)
Đảm bảo file `.env` của `careerpath-fastapi` trên server có cùng `SECRET_KEY`:
```ini
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
```
Khởi động lại Backend CareerPath:
```bash
sudo systemctl restart careerpath-fastapi
```

### 2.4. Build & Deploy CareerPath Frontend (`careerpath-react-ts-vite`)
1. Cấu hình file `.env.production` tại thư mục frontend:
   ```ini
   VITE_AUTH_API_URL=https://english-practice.tma.com.vn/api/auth
   VITE_API_URL=https://english-practice.tma.com.vn/careerpath/api
   ```
2. Build và deploy:
   ```bash
   cd careerpath-react-ts-vite
   npm run build
   # Copy thư mục dist/ sang web root của CareerPath trên server
   ```

### ✅ Checklist nghiệm thu Giai đoạn 2:
1. Mở trình duyệt vào `https://english-practice.tma.com.vn/careerpath/login`.
2. Đăng nhập bằng tài khoản **đã có sẵn từ TOEIC** $\rightarrow$ Đăng nhập thành công, CareerPath tự khởi tạo Profile tương ứng (Auto-provisioning).
3. Đăng ký tài khoản **mới** $\rightarrow$ Hệ thống gửi OTP về email $\rightarrow$ Xác thực và tạo tài khoản thành công.
4. Làm bài Quiz / Onboarding $\rightarrow$ Dữ liệu lưu chính xác vào `toeic_learningpath` DB.

---

## 🔄 GIAI ĐOẠN 3: Chuyển Đổi TOEIC & Kích Hoạt SSO (Zero Downtime)

> **Mục tiêu**: Đưa TOEIC sang dùng Auth Service mà không làm gián đoạn các phiên làm bài thi của học viên đang học.

### 3.1. Cập nhật TOEIC Backend
Cập nhật module xác thực JWT trên backend TOEIC sử dụng chung `JWT_SECRET_KEY` với thuật toán HS256:
```python
# TOEIC Backend auth dependency:
def get_current_user(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            issuer="https://english-practice.tma.com.vn/auth",
            options={"verify_aud": False},
        )
        return get_or_sync_user(payload)
    except Exception:
        raise AuthenticationFailed("Token không hợp lệ hoặc đã hết hạn")
```
Khởi động lại Backend TOEIC.

### 3.2. Cập nhật TOEIC Frontend
Cập nhật file `authService.ts` trên TOEIC Frontend:
* Chuyển các endpoint API đăng nhập/đăng ký sang `/api/auth/login`, `/api/auth/register`.
* Build và deploy phiên bản frontend mới.

### 3.3. Kiểm thử Single Sign-On (SSO) toàn hệ thống:
1. Đăng nhập tại **TOEIC**: `https://english-practice.tma.com.vn/login`.
2. Mở tab mới truy cập **CareerPath**: `https://english-practice.tma.com.vn/careerpath/` $\rightarrow$ **Tự động đăng nhập, nhận diện đúng User không cần nhập lại mật khẩu**.
3. Bấm **Đăng xuất (Logout)** ở một tab $\rightarrow$ Cả hai ứng dụng đều hủy phiên làm việc an toàn.

---

## 🛡️ KẾ HOẠCH HOÀN NGUYÊN (ROLLBACK PLAN < 1 PHÚT)

Nếu phát sinh sự cố ở bất kỳ bước nào:

| Tình huống | Thao tác Rollback | Thời gian |
| :--- | :--- | :--- |
| **Sự cố Giai đoạn 1** | `sudo systemctl stop auth-service` — Hệ thống hiện tại không bị ảnh hưởng. | 5 giây |
| **Sự cố Giai đoạn 2** | Comment block `location /api/auth/` trong file Nginx $\rightarrow$ `sudo systemctl reload nginx`. | 30 giây |
| **Sự cố Giai đoạn 3** | Rollback bản build frontend/backend TOEIC về commit trước đó. | 1 phút |

---

## 📊 BẢNG ĐỐI CHIẾU CẤU HÌNH LOCAL VS PRODUCTION

| Thuộc tính | Môi Trường Local (Dev - Windows / Linux) | Môi Trường Server (Production - Linux) |
| :--- | :--- | :--- |
| **Domain Host** | `localhost` / `127.0.0.1` | `english-practice.tma.com.vn` |
| **MySQL Host** | `localhost:3306` | `127.0.0.1:3306` |
| **Database Name** | `auth_db` | `auth_db` |
| **Cookie Domain** | `localhost` | `english-practice.tma.com.vn` |
| **Cookie Secure** | `false` (HTTP) | `true` (HTTPS bắt buộc) |
| **Cookie SameSite** | `lax` | `lax` |
| **Bắt buộc OTP khi ĐK** | `false` (tiện test) | `true` (bảo mật production) |
| **JWT Algorithm** | `HS256` | `HS256` |
| **JWT Secret Key** | Dùng chung trong `.env` | Dùng chung trong `.env` trên Server |
| **JWT Issuer** | `https://english-practice.tma.com.vn/auth` | `https://english-practice.tma.com.vn/auth` |
| **Uvicorn Runner** | `--reload --host 0.0.0.0` | `--workers 2 --host 127.0.0.1` qua Systemd |
