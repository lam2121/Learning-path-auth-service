# CareerPath — Central Auth Microservice

Centralized Authentication & Single Sign-On (**Identity Provider & SSO**) service for the **CareerPath Platform**.

---

## 1. Prerequisites

* **Python**: 3.10+ (Recommended Python 3.12)
* **MySQL Server**: 8.0+
* **Redis Server**: 6.0+ (Session token caching & OTP rate limiting)

---

## 2. Installation & Setup

### Step 1: Navigate to directory
```bash
cd Learning-path-auth-service
```

### Step 2: Create & activate virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure environment `.env`
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment configuration:
```ini
# ── Database ──────────────────────────────────────────────
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=auth_db
MYSQL_PORT=3306

# ── Redis ─────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── JWT HS256 ─────────────────────────────────────────────
JWT_SECRET_KEY=your_generated_64_character_hex_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=https://careerpath.local/auth
JWT_AUDIENCE=toeic,careerpath

# ── OTP & Rate Limit ──────────────────────────────────────
REQUIRE_REGISTER_OTP=false
OTP_EXPIRES_MINUTES=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_MINUTES=10
OTP_MAX_VERIFY_ATTEMPTS=5

# ── SMTP (Email OTP) ──────────────────────────────────────
EMAIL_SENDER=support@careerpath.io
EMAIL_USERNAME=support@careerpath.io
EMAIL_PASSWORD=your_email_password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# ── Cookie (SSO) ──────────────────────────────────────────
COOKIE_DOMAIN=localhost
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

### Step 5: Initialize Database & Run Alembic Migrations
```bash
# Run Alembic migrations
alembic upgrade head
```

---

## 3. Running the Service

### Development Mode (with auto-reload)
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
Interactive docs available at: `http://localhost:8001/docs`.

---

## 4. Testing

Run automated test suite:
```powershell
pytest tests/ -v
```

---

## 5. Main API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service root and metadata |
| `GET` | `/health` | Healthcheck endpoint |
| `POST` | `/api/auth/register` | User registration |
| `POST` | `/api/auth/register/otp` | Send registration OTP verification |
| `POST` | `/api/auth/login` | Login (Email/Username) $\rightarrow$ JWT Token & HttpOnly Cookie |
| `POST` | `/api/auth/refresh-token`| Refresh access token (from HttpOnly Cookie or Bearer) |
| `POST` | `/api/auth/logout` | Logout (revokes refresh token and clears cookie) |
| `POST` | `/api/auth/password/otp` | Send password reset OTP |
| `POST` | `/api/auth/password/otp/verify` | Verify password reset OTP |
| `PUT` | `/api/auth/password/reset` | Reset password |
| `GET` | `/api/auth/me` | Current user profile |
| `GET` | `/api/auth/verify-token` | Internal token verification for downstream services |
