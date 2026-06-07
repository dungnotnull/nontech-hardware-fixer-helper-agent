"""arXiv paper crawler for appliance diagnosis research."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import aiohttp
import feedparser
from loguru import logger


class ArxivCrawler:
    """Fetch appliance-relevant papers from arXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"
    DEFAULT_QUERIES = [
        "appliance fault diagnosis deep learning",
        "visual error detection home electronics",
        "multimodal device troubleshooting",
        "consumer electronics repair automation",
    ]

    def __init__(self, max_papers_per_run: int = 20) -> None:
        self.max_papers = max_papers_per_run

    async def crawl(
        self,
        queries: list[str] | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        queries = queries or self.DEFAULT_QUERIES
        max_results = max_results or self.max_papers
        all_papers: list[dict[str, Any]] = []
        per_query = max(1, max_results // len(queries))

        async with aiohttp.ClientSession() as session:
            for q in queries:
                papers = await self._fetch_query(session, q, per_query)
                all_papers.extend(papers)
                if len(all_papers) >= max_results:
                    break

        # Deduplicate by arXiv ID
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for p in all_papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                unique.append(p)

        logger.info(f"arXiv crawl complete: {len(unique)} unique papers")
        return unique[:max_results]

    async def _fetch_query(self, session: aiohttp.ClientSession, query: str, limit: int) -> list[dict[str, Any]]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                text = await resp.text()
        except Exception as e:
            logger.warning(f"arXiv fetch failed for '{query}': {e}")
            return []

        feed = feedparser.parse(text)
        papers: list[dict[str, Any]] = []
        for entry in feed.entries:
            arxiv_id = entry.get("id", "").split("/")[-1].split("v")[0]
            papers.append({
                "arxiv_id": arxiv_id,
                "title": entry.get("title", "").replace("\n", " "),
                "authors": [a.get("name", "") for a in entry.get("authors", [])],
                "summary": entry.get("summary", "").replace("\n", " "),
                "published": entry.get("published", ""),
                "pdf_link": next((l.href for l in entry.get("links", []) if l.get("type") == "application/pdf"), ""),
                "source": "arxiv",
                "query": query,
                "crawled_at": datetime.utcnow().isoformat(),
            })
        return papers