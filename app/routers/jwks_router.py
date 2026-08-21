"""JWKS endpoint — expose the RS256 public key for external verification."""

from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.security import get_public_key

router = APIRouter()


@router.get("/.well-known/jwks.json")
async def jwks():
    """Return the JSON Web Key Set containing the RS256 public key.

    TOEIC and CareerPath backends can fetch this endpoint to obtain the public
    key used to verify JWT tokens issued by this Auth Service.
    """
    pub_key = load_pem_public_key(get_public_key().encode())
    pub_numbers = pub_key.public_numbers()

    def _int_to_base64url(n: int) -> str:
        byte_length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_length, byteorder="big")).rstrip(b"=").decode()

    jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": "auth-service-key-1",
        "n": _int_to_base64url(pub_numbers.n),
        "e": _int_to_base64url(pub_numbers.e),
    }

    return JSONResponse(content={"keys": [jwk]})
