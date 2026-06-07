"""Rate limiting using a sliding window in Redis (or in-memory fallback)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, Request, status
from loguru import logger


class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(
        self,
        redis_client: Any | None = None,
        max_requests: int = 30,
        window_seconds: int = 60,
    ) -> None:
        self.redis = redis_client
        self.max_requests = max_requests
        self.window = window_seconds
        self._local_store: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.zremrangebyscore(key, 0, now - self.window)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, self.window)
                _, _, count, _ = pipe.execute()
                return count <= self.max_requests
            except Exception as e:
                logger.warning(f"Redis rate limit failed: {e}; falling back to memory")
                self.redis = None

        # In-memory fallback
        window = self._local_store.setdefault(key, [])
        window[:] = [t for t in window if now - t < self.window]
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True

    def check(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        if not self.is_allowed(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
            )