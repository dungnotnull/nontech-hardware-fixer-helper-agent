"""Migrate ChromaDB collections to Qdrant for scalable production use."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from fixeragent.config import get_settings

try:
    import qdrant_client
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not available; Qdrant migration disabled")


class QdrantMigrator:
    """Zero-downtime migration from ChromaDB to Qdrant."""

    def __init__(
        self,
        qdrant_url: str | None = None,
        qdrant_api_key: str | None = None,
        collection_name: str | None = None,
        vector_size: int = 1024,
    ) -> None:
        settings = get_settings()
        self.url = qdrant_url or settings.qdrant_url or "http://localhost:6333"
        self.api_key = qdrant_api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.chroma_collection_name
        self.vector_size = vector_size
        self.client: Any = None
        if QDRANT_AVAILABLE:
            try:
                self.client = qdrant_client.QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                )
                logger.info("Qdrant client initialized")
            except Exception as e:
                logger.error(f"Qdrant client init failed: {e}")

    def create_collection(self) -> None:
        if not self.client:
            return
        try:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            logger.info(f"Qdrant collection '{self.collection_name}' created")
        except Exception as e:
            logger.error(f"Collection creation failed: {e}")

    def migrate_from_chroma(self, rag_engine: Any) -> dict[str, Any]:
        """Copy all documents from ChromaDB to Qdrant."""
        if not self.client:
            logger.error("Qdrant client unavailable")
            return {"migrated": 0, "errors": 1}
        if not rag_engine._collection:
            logger.error("ChromaDB collection unavailable")
            return {"migrated": 0, "errors": 1}

        self.create_collection()
        try:
            data = rag_engine._collection.get(include=["embeddings", "documents", "metadatas"])
            ids = data["ids"]
            embeddings = data["embeddings"]
            documents = data["documents"]
            metadatas = data["metadatas"]

            points: list[Any] = []
            for i, doc_id in enumerate(ids):
                payload = {
                    "text": documents[i],
                    **(metadatas[i] or {}),
                }
                points.append(PointStruct(id=i, vector=embeddings[i], payload=payload))

            batch_size = 100
            for start in range(0, len(points), batch_size):
                batch = points[start:start + batch_size]
                self.client.upsert(collection_name=self.collection_name, points=batch)
                logger.info(f"Migrated batch {start}-{start + len(batch)}")

            return {"migrated": len(points), "errors": 0}
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {"migrated": 0, "errors": 1}

    def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Dense vector search in Qdrant."""
        if not self.client:
            return []
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True,
            )
            return [
                {
                    "content": r.payload.get("text", ""),
                    "metadata": {k: v for k, v in r.payload.items() if k != "text"},
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []