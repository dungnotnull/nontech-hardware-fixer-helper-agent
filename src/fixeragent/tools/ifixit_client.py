"""iFixit API client for repair guide crawling."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import aiohttp
from loguru import logger


class iFixitClient:
    """Fetch repair guides from iFixit public API."""

    BASE_URL = "https://www.ifixit.com/api/2.0"
    CATEGORIES = [
        "Electronics",
        "Appliance",
        "Computer Hardware",
        "Camera",
        "Phone",
        "Tablet",
    ]

    async def crawl(
        self,
        max_guides: int = 50,
        difficulty: str | None = "moderate",
    ) -> list[dict[str, Any]]:
        """Crawl newest repair guides from iFixit."""
        guides: list[dict[str, Any]] = []
        async with aiohttp.ClientSession() as session:
            for category in self.CATEGORIES:
                batch = await self._fetch_category(session, category, max_per_category=15, difficulty=difficulty)
                guides.extend(batch)
                if len(guides) >= max_guides:
                    break
        logger.info(f"iFixit crawl complete: {len(guides)} guides")
        return guides[:max_guides]

    async def _fetch_category(
        self,
        session: aiohttp.ClientSession,
        category: str,
        max_per_category: int,
        difficulty: str | None,
    ) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/guides"
        params: dict[str, Any] = {
            "category": category,
            "limit": max_per_category,
            "sort": "date",
            "order": "desc",
        }
        if difficulty:
            params["difficulty"] = difficulty
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                data = await resp.json()
        except Exception as e:
            logger.warning(f"iFixit fetch failed for {category}: {e}")
            return []

        results: list[dict[str, Any]] = []
        for g in data.get("guides", []):
            results.append({
                "guide_id": g.get("guideid"),
                "title": g.get("title", ""),
                "category": category,
                "difficulty": g.get("difficulty", ""),
                "summary": g.get("summary", ""),
                "url": g.get("url", ""),
                "image": g.get("image", {}).get("thumbnail", ""),
                "source": "ifixit",
                "crawled_at": datetime.utcnow().isoformat(),
            })
        return results