"""Manufacturer RSS feed scraper for support bulletins."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp
import feedparser
from loguru import logger


class RSSBulletinScraper:
    """Scrape manufacturer support RSS feeds."""

    DEFAULT_FEEDS: dict[str, str] = {
        "HP": "https://support.hp.com/us-en/rss",
        "Canon": "https://www.usa.canon.com/rss",
        "Samsung": "https://news.samsung.com/global/rss",
        "Bosch": "https://www.bosch-home.com/rss",
        "Philips": "https://www.philips.com/global/rss",
    }

    def __init__(self, feeds: dict[str, str] | None = None) -> None:
        self.feeds = feeds or self.DEFAULT_FEEDS

    async def crawl(self, max_per_feed: int = 10) -> list[dict[str, Any]]:
        bulletins: list[dict[str, Any]] = []
        async with aiohttp.ClientSession() as session:
            for brand, url in self.feeds.items():
                items = await self._fetch_feed(session, brand, url, max_per_feed)
                bulletins.extend(items)
        logger.info(f"RSS crawl complete: {len(bulletins)} bulletins")
        return bulletins

    async def _fetch_feed(
        self,
        session: aiohttp.ClientSession,
        brand: str,
        url: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
        except Exception as e:
            logger.warning(f"RSS fetch failed for {brand}: {e}")
            return []

        feed = feedparser.parse(text)
        results: list[dict[str, Any]] = []
        for entry in feed.entries[:limit]:
            results.append({
                "brand": brand,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "source": "rss",
                "crawled_at": datetime.utcnow().isoformat(),
            })
        return results