"""Authentication and API key validation for admin endpoints."""

from __future__ import annotations

import secrets
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status
from loguru import logger


class APIKeyAuth:
    """Simple API key bearer auth for admin endpoints."""

    def __init__(self, valid_keys: list[str] | None = None) -> None:
        self.valid_keys = set(valid_keys or [])

    def add_key(self, key: str) -> None:
        self.valid_keys.add(key)

    def validate(self, request: Request) -> bool:
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return False
        token = auth[7:].strip()
        return token in self.valid_keys


def require_admin(api_key_auth: APIKeyAuth):
    """FastAPI dependency decorator for admin-only endpoints."""
    def dependency(request: Request) -> None:
        if not api_key_auth.validate(request):
            logger.warning(f"Unauthorized admin request from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing admin API key",
            )
    return dependency