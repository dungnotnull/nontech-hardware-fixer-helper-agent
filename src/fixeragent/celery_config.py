"""Celery configuration for async background tasks."""

from __future__ import annotations

from fixeragent.config import get_settings

settings = get_settings()

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except Exception:
    CELERY_AVAILABLE = False

if CELERY_AVAILABLE:
    celery_app = Celery(
        "fixeragent",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["fixeragent.tasks"],
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,
        worker_prefetch_multiplier=1,
    )
else:
    celery_app = None