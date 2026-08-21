"""Algorithm metadata endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import app_config

router = APIRouter()


@router.get("/.well-known/jwks.json")
async def jwks():
    """Return JSON Web Key info for Resource Servers."""
    return JSONResponse(
        content={
            "algorithm": app_config.JWT_ALGORITHM,
            "issuer": app_config.JWT_ISSUER,
            "audience": app_config.JWT_AUDIENCE.split(","),
            "message": "Auth Service uses HS256 symmetric signing with JWT_SECRET_KEY.",
            "keys": [],
        }
    )
