"""Auth Microservice — Central Identity Provider & SSO for TMA English Practice."""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import auth_router, jwks_router, user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup (development only).
    In production, use Alembic migrations instead."""
    if os.getenv("APP_ENV", "development").lower() != "production":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="TMA English Practice — Auth Service",
    description="Central Identity Provider & SSO Service for TOEIC and CareerPath applications.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://english-practice.tma.com.vn",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|english-practice\.tma\.com\.vn)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user_router.router, prefix="/api/auth", tags=["User"])
app.include_router(jwks_router.router, tags=["JWKS"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "auth-service"}
