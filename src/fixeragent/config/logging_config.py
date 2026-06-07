"""Loguru-based logging configuration."""

import sys
from pathlib import Path

from loguru import logger

from .settings import get_settings


def configure_logging() -> None:
    """Configure Loguru with file + stderr sinks."""
    settings = get_settings()
    logger.remove()

    # stderr - human-readable
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level:<8}</level> | "
               "<cyan>{name}:{line}</cyan> - {message}",
    )

    # file - structured / persistent
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )
