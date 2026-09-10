"""Auth Microservice — Central Identity Provider & SSO for CareerPath Platform."""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import app_config
from app.core.database import Base, engine
from app.routers import auth_router, user_router

INSECURE_EXAMPLE_SECRET = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"


def _validate_jwt_secret() -> None:
    secret = getattr(app_config, "JWT_SECRET_KEY", "")
    if secret == INSECURE_EXAMPLE_SECRET:
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Server refused to boot because JWT_SECRET_KEY "
                "matches the hardcoded insecure example key in production. Generate a strong key with: "
                "python -c 'import secrets; print(secrets.token_hex(32))' and set it in your .env file."
            )
        import logging
        logging.getLogger("uvicorn.error").warning(
            "SECURITY WARNING: JWT_SECRET_KEY is using the hardcoded default key from .env.example! "
            "Change this immediately before deploying to production."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration and initialize tables on startup."""
    _validate_jwt_secret()
    if os.getenv("APP_ENV", "development").lower() != "production":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CareerPath — Auth Service",
    description="Central Identity Provider & SSO Service for CareerPath applications.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://builtbylam.com",
        "https://www.builtbylam.com",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user_router.router, prefix="/api/auth", tags=["User"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "CareerPath — Auth Microservice",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/auth/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "auth-service"}
