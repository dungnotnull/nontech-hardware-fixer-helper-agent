"""Redis caching layer for frequent queries and session state."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from fixeragent.config import get_settings

try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    logger.warning("redis not available; caching disabled")


class RedisCache:
    """Simple Redis-backed cache with TTL."""

    def __init__(self, url: str | None = None) -> None:
        settings = get_settings()
        self.url = url or settings.redis_url
        self.client: Any = None
        if REDIS_AVAILABLE:
            try:
                self.client = redis.from_url(self.url, decode_responses=True)
                self.client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis cache connection failed: {e}")

    def get(self, key: str) -> Any | None:
        if not self.client:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        if not self.client:
            return
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    def delete(self, key: str) -> None:
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False