"""Weekly knowledge update pipeline."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from fixeragent.config import get_settings
from fixeragent.tools.arxiv_crawler import ArxivCrawler
from fixeragent.tools.ifixit_client import iFixitClient
from fixeragent.tools.rag_engine import RAGEngine
from fixeragent.tools.repairclinic_scraper import RepairClinicScraper
from fixeragent.tools.rss_scraper import RSSBulletinScraper

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except Exception:
    ST_AVAILABLE = False


class KnowledgeUpdater:
    """Orchestrate weekly crawl → filter → embed → index pipeline."""

    def __init__(
        self,
        rag: RAGEngine | None = None,
        relevance_threshold: float = 0.70,
    ) -> None:
        self.settings = get_settings()
        self.rag = rag or RAGEngine()
        self.relevance_threshold = relevance_threshold
        self.embedder: Any = None
        if ST_AVAILABLE:
            try:
                self.embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")
            except Exception as e:
                logger.warning(f"Embedder init failed: {e}")

    async def run(self, dry_run: bool = False) -> dict[str, Any]:
        """Run the full knowledge update pipeline."""
        logger.info(f"Knowledge updater starting (dry_run={dry_run})")
        errors: list[str] = []
        added = 0
        sources: list[str] = []

        # 1. Crawl all sources
        crawled = await self._crawl_all()

        # 2. Filter for relevance
        filtered = self._filter_relevance(crawled)

        # 3. Deduplicate
        unique = self._deduplicate(filtered)

        # 4. Add to knowledge base
        if not dry_run:
            for doc in unique:
                try:
                    self.rag.add_documents([doc["content"]], [doc["metadata"]])
                    added += 1
                except Exception as e:
                    errors.append(f"Add failed for {doc.get('id', '?')}: {e}")
            self.rag.persist()
            self._update_brain_md(unique)
        else:
            added = len(unique)
            logger.info(f"Dry run: would add {added} documents")

        sources = list({d["metadata"]["source"] for d in unique})
        status = {
            "last_run": datetime.utcnow().isoformat(),
            "documents_added": added,
            "errors": errors,
            "sources_crawled": sources,
        }
        self._save_status(status)
        logger.info(f"Pipeline complete: {added} docs added, {len(errors)} errors")
        return status

    async def _crawl_all(self) -> list[dict[str, Any]]:
        crawlers = {
            "arxiv": ArxivCrawler(),
            "ifixit": iFixitClient(),
            "rss": RSSBulletinScraper(),
            "repairclinic": RepairClinicScraper(),
        }
        raw: list[dict[str, Any]] = []
        for name, crawler in crawlers.items():
            try:
                if name == "arxiv":
                    items = await crawler.crawl()
                elif name == "ifixit":
                    items = await crawler.crawl()
                elif name == "rss":
                    items = await crawler.crawl()
                elif name == "repairclinic":
                    items = await crawler.crawl()
                else:
                    continue
                for item in items:
                    item["metadata"] = {"source": name, **item}
                    item["content"] = self._item_to_text(item)
                    item["id"] = self._hash(item["content"])
                raw.extend(items)
                logger.info(f"Crawled {len(items)} from {name}")
            except Exception as e:
                logger.error(f"Crawler {name} failed: {e}")
        return raw

    def _filter_relevance(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.embedder:
            logger.warning("No embedder; skipping relevance filter")
            return items
        target_texts = [
            "appliance repair",
            "home device troubleshooting",
            "DIY repair guide",
            "fault diagnosis",
            "consumer electronics maintenance",
        ]
        target_emb = self.embedder.encode(target_texts, normalize_embeddings=True)
        filtered: list[dict[str, Any]] = []
        for item in items:
            try:
                emb = self.embedder.encode([item["content"]], normalize_embeddings=True)
                sim = float(max(emb @ target_emb.T))
                if sim >= self.relevance_threshold:
                    item["metadata"]["relevance_score"] = round(sim, 4)
                    filtered.append(item)
            except Exception:
                continue
        logger.info(f"Relevance filter: {len(filtered)} / {len(items)} passed")
        return filtered

    def _deduplicate(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in items:
            h = item.get("id") or self._hash(item["content"])
            if h not in seen:
                seen.add(h)
                item["id"] = h
                unique.append(item)
        logger.info(f"Deduplication: {len(unique)} / {len(items)} unique")
        return unique

    @staticmethod
    def _item_to_text(item: dict[str, Any]) -> str:
        parts = [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("description", ""),
            item.get("url", ""),
        ]
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _update_brain_md(self, items: list[dict[str, Any]]) -> None:
        brain_path = Path(self.settings.knowledge_brain_path)
        if not brain_path.exists():
            return
        try:
            with open(brain_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n## Auto-Crawl Append — {datetime.utcnow().isoformat()}\n\n")
                for item in items[:20]:
                    f.write(f"### {item.get('title', 'Untitled')}\n")
                    f.write(f"**Source**: {item['metadata'].get('source', 'unknown')}\n")
                    f.write(f"**URL**: {item.get('url', 'N/A')}\n")
                    f.write(f"**Status**: [COMMUNITY] **Confidence**: {item['metadata'].get('relevance_score', 0.0)}\n")
                    f.write(f"**Last Updated**: {datetime.utcnow().strftime('%Y-%m-%d')}\n\n")
                    f.write(f"{item['content'][:500]}\n\n")
            logger.info("Knowledge brain markdown updated")
        except Exception as e:
            logger.warning(f"Brain markdown update failed: {e}")

    def _save_status(self, status: dict[str, Any]) -> None:
        cache_path = Path(self.settings.chroma_persist_dir) / "crawl_status.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="FixerAgent Knowledge Updater")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing.")
    args = parser.parse_args()
    updater = KnowledgeUpdater()
    asyncio.run(updater.run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()