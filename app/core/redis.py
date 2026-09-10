"""Production-grade Redis module for Auth Microservice.

Provides:
- Synchronous and asynchronous Redis client singletons with connection pooling.
- 2.0s socket timeout preventing request hangs on Redis degradation.
- Resilient caching and token blacklist helpers with graceful degradation.
- Safe fallbacks so authentication/DB operations succeed even if Redis is unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.config import app_config

try:
    import redis
    import redis.asyncio as aioredis
except ImportError:
    redis = None
    aioredis = None

logger = logging.getLogger(__name__)

_async_redis_client: Optional[aioredis.Redis] = None
_sync_redis_client: Optional[redis.Redis] = None


def get_redis_async() -> Optional[aioredis.Redis]:
    """Get or create singleton async Redis client with 2s timeout."""
    global _async_redis_client
    if not app_config.REDIS_URL or aioredis is None:
        return None

    if _async_redis_client is None:
        try:
            _async_redis_client = aioredis.from_url(
                app_config.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=True,
            )
        except Exception as exc:
            logger.warning(f"[Auth Redis Async] Connection initialization failed: {exc}")
            return None
    return _async_redis_client


def get_redis_sync() -> Optional[redis.Redis]:
    """Get or create singleton synchronous Redis client with 2s timeout."""
    global _sync_redis_client
    if not app_config.REDIS_URL or redis is None:
        return None

    if _sync_redis_client is None:
        try:
            _sync_redis_client = redis.from_url(
                app_config.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=True,
            )
        except Exception as exc:
            logger.warning(f"[Auth Redis Sync] Connection initialization failed: {exc}")
            return None
    return _sync_redis_client


# ── Sync Cache Helpers ────────────────────────────────────────────────────────

def sync_get_cache(key: str) -> Any | None:
    """Retrieve and deserialize a JSON cached value. Returns None on cache miss or error."""
    client = get_redis_sync()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw
    except Exception as exc:
        logger.warning(f"[Auth Redis Cache] sync_get_cache('{key}') failed: {exc}")
        return None


def sync_set_cache(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Serialize and store a value with TTL. Returns False on failure without raising."""
    client = get_redis_sync()
    if client is None:
        return False
    try:
        data = value if isinstance(value, str) else json.dumps(value, default=str)
        client.set(key, data, ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning(f"[Auth Redis Cache] sync_set_cache('{key}') failed: {exc}")
        return False


def sync_delete_cache(key: str) -> bool:
    """Delete a key from Redis."""
    client = get_redis_sync()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception as exc:
        logger.warning(f"[Auth Redis Cache] sync_delete_cache('{key}') failed: {exc}")
        return False


# ── Token Blacklist / Revocation Helpers ──────────────────────────────────────

def blacklist_token(jti: str, ttl_seconds: int) -> bool:
    """Add a JWT ID (jti) to the revoked tokens blacklist."""
    return sync_set_cache(f"blacklist:jti:{jti}", "revoked", ttl_seconds=ttl_seconds)


def is_token_blacklisted(jti: str) -> bool:
    """Check whether a JWT ID (jti) has been revoked."""
    res = sync_get_cache(f"blacklist:jti:{jti}")
    return res is not None
