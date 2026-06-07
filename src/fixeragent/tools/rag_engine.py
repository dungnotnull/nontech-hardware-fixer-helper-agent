"""RAG Engine — hybrid dense + sparse retrieval from knowledge corpus."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

from loguru import logger

from fixeragent.config import get_settings
from fixeragent.models import RetrievalChunk
from fixeragent.tools.chunker import TextChunker
from fixeragent.tools.pdf_ingestor import PDFIngestor

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB not available; RAG will operate in degraded mode")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available; dense retrieval disabled")

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except Exception:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not available; sparse retrieval disabled")

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except Exception:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("cross-encoder not available; reranking disabled")


class RAGEngine:
    """Retrieve repair procedures using hybrid dense+sparse search + reranking."""

    EMBED_MODEL = "BAAI/bge-large-en-v1.5"
    RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    DEFAULT_TOP_K = 5
    MIN_RELEVANCE = 0.72

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        collection_name: str | None = None,
        embed_model: str | None = None,
        rerank_model: str | None = None,
    ) -> None:
        self.settings = get_settings()
        self.persist_dir = Path(persist_dir or self.settings.chroma_persist_dir)
        self.collection_name = collection_name or self.settings.chroma_collection_name
        self.embed_model_name = embed_model or self.EMBED_MODEL
        self.rerank_model_name = rerank_model or self.RERANK_MODEL

        self._chroma_client: Any = None
        self._collection: Any = None
        self._embedder: Any = None
        self._bm25: Any = None
        self._corpus_texts: list[str] = []
        self._corpus_metas: list[dict[str, Any]] = []
        self._reranker: Any = None
        self._chunker = TextChunker()
        self._pdf_ingestor = PDFIngestor(chunker=self._chunker)

        self._init_chroma()
        self._init_embedder()
        self._init_reranker()
        self._load_or_build_bm25()

    # -----------------------------------------------------------------
    # Initializers
    # -----------------------------------------------------------------

    def _init_chroma(self) -> None:
        if not CHROMA_AVAILABLE:
            return
        try:
            self._chroma_client = chromadb.Client(
                ChromaSettings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(self.persist_dir),
                    anonymized_telemetry=False,
                )
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB collection '{self.collection_name}' ready")
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")

    def _init_embedder(self) -> None:
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return
        try:
            self._embedder = SentenceTransformer(self.embed_model_name)
            logger.info(f"Embedding model loaded: {self.embed_model_name}")
        except Exception as e:
            logger.error(f"Embedding model load failed: {e}")

    def _init_reranker(self) -> None:
        if not CROSS_ENCODER_AVAILABLE:
            return
        try:
            self._reranker = CrossEncoder(self.rerank_model_name)
            logger.info(f"Reranker loaded: {self.rerank_model_name}")
        except Exception as e:
            logger.error(f"Reranker load failed: {e}")

    def _load_or_build_bm25(self) -> None:
        bm25_path = self.persist_dir / "bm25_index.pkl"
        corpus_path = self.persist_dir / "bm25_corpus.json"
        if bm25_path.exists() and corpus_path.exists():
            try:
                with open(bm25_path, "rb") as f:
                    self._bm25 = pickle.load(f)
                with open(corpus_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._corpus_texts = data["texts"]
                    self._corpus_metas = data["metas"]
                logger.info(f"BM25 index loaded: {len(self._corpus_texts)} docs")
            except Exception as e:
                logger.warning(f"BM25 load failed: {e}; will rebuild on next add")

    # -----------------------------------------------------------------
    # Ingestion
    # -----------------------------------------------------------------

    def add_documents(self, documents: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:
        """Ingest documents into vector store + BM25 index."""
        if not documents:
            return
        metadatas = metadatas or [{} for _ in documents]
        self._corpus_texts.extend(documents)
        self._corpus_metas.extend(metadatas)

        # Dense embeddings via ChromaDB
        if CHROMA_AVAILABLE and self._collection and self._embedder:
            try:
                embeddings = self._embedder.encode(documents, normalize_embeddings=True).tolist()
                ids = [f"doc_{self._collection.count() + i}" for i in range(len(documents))]
                self._collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
                logger.info(f"Added {len(documents)} docs to ChromaDB")
            except Exception as e:
                logger.error(f"ChromaDB add failed: {e}")

        # Sparse BM25 index rebuild
        if BM25_AVAILABLE:
            try:
                tokenized = [d.lower().split() for d in self._corpus_texts]
                self._bm25 = BM25Okapi(tokenized)
                self._persist_bm25()
                logger.info(f"BM25 index rebuilt: {len(self._corpus_texts)} docs")
            except Exception as e:
                logger.error(f"BM25 rebuild failed: {e}")

    def add_pdf(self, pdf_path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        """Ingest a PDF manual into the knowledge corpus."""
        chunks = self._pdf_ingestor.ingest(pdf_path, metadata)
        texts = [c["text"] for c in chunks]
        metas = [c["metadata"] for c in chunks]
        self.add_documents(texts, metas)

    def ingest_directory(self, directory: str | Path, glob: str = "*.pdf") -> None:
        """Batch ingest all PDFs in a directory."""
        directory = Path(directory)
        files = list(directory.rglob(glob))
        logger.info(f"Ingesting {len(files)} PDFs from {directory}")
        for pdf_file in files:
            brand = pdf_file.parent.name
            self.add_pdf(pdf_file, metadata={"brand": brand, "source_path": str(pdf_file)})

    # -----------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.72) -> list[RetrievalChunk]:
        """Hybrid retrieval: dense semantic + sparse BM25 + cross-encoder rerank."""
        logger.info(f"Retrieving for query: {query!r}")
        dense_results = self._dense_retrieve(query, top_k=top_k * 3)
        sparse_results = self._sparse_retrieve(query, top_k=top_k * 3)
        fused = self._reciprocal_rank_fusion(dense_results, sparse_results, k=60)
        reranked = self._rerank(query, fused, top_k=top_k)
        # Filter by min relevance
        filtered = [r for r in reranked if (r.rerank_score or r.fused_score) >= min_score]
        logger.info(f"Retrieved {len(filtered)} chunks after hybrid fusion + rerank")
        return filtered

    def _dense_retrieve(self, query: str, top_k: int) -> list[RetrievalChunk]:
        if not (CHROMA_AVAILABLE and self._collection and self._embedder):
            return []
        try:
            q_emb = self._embedder.encode([query], normalize_embeddings=True).tolist()
            results = self._collection.query(query_embeddings=q_emb, n_results=top_k, include=["documents", "metadatas", "distances"])
            chunks: list[RetrievalChunk] = []
            for i in range(len(results["documents"][0])):
                dist = results["distances"][0][i]
                score = 1.0 - float(dist)  # cosine distance → similarity
                chunks.append(RetrievalChunk(
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    dense_score=score,
                ))
            return chunks
        except Exception as e:
            logger.error(f"Dense retrieval failed: {e}")
            return []

    def _sparse_retrieve(self, query: str, top_k: int) -> list[RetrievalChunk]:
        if not (BM25_AVAILABLE and self._bm25):
            return []
        try:
            tokenized_query = query.lower().split()
            scores = self._bm25.get_scores(tokenized_query)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            chunks: list[RetrievalChunk] = []
            for idx in top_indices:
                chunks.append(RetrievalChunk(
                    content=self._corpus_texts[idx],
                    metadata=self._corpus_metas[idx],
                    sparse_score=float(scores[idx]),
                ))
            return chunks
        except Exception as e:
            logger.error(f"Sparse retrieval failed: {e}")
            return []

    @staticmethod
    def _reciprocal_rank_fusion(
        dense: list[RetrievalChunk],
        sparse: list[RetrievalChunk],
        k: int = 60,
    ) -> list[RetrievalChunk]:
        """Fuse two ranked lists using RRF."""
        scores: dict[str, float] = {}
        contents: dict[str, RetrievalChunk] = {}

        def add_ranked(chunks: list[RetrievalChunk], rank_weight: float = 1.0) -> None:
            for rank, chunk in enumerate(chunks, start=1):
                key = chunk.content
                if key not in contents:
                    contents[key] = chunk
                scores[key] = scores.get(key, 0.0) + rank_weight / (k + rank)

        add_ranked(dense, rank_weight=1.0)
        add_ranked(sparse, rank_weight=1.0)

        # Update fused scores back into chunk objects
        for key, chunk in contents.items():
            chunk.fused_score = scores.get(key, 0.0)

        sorted_chunks = sorted(contents.values(), key=lambda c: c.fused_score, reverse=True)
        return sorted_chunks

    def _rerank(self, query: str, chunks: list[RetrievalChunk], top_k: int) -> list[RetrievalChunk]:
        if not (CROSS_ENCODER_AVAILABLE and self._reranker and chunks):
            return chunks[:top_k]
        try:
            pairs = [(query, c.content) for c in chunks]
            scores = self._reranker.predict(pairs)
            for chunk, score in zip(chunks, scores):
                chunk.rerank_score = float(score)
            sorted_chunks = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
            return sorted_chunks[:top_k]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return chunks[:top_k]

    def load_knowledge_brain(self, brain_path: str | Path | None = None) -> None:
        """Parse SECOND-KNOWLEDGE-BRAIN.md and index knowledge atoms."""
        path = Path(brain_path or self.settings.knowledge_brain_path)
        if not path.exists():
            logger.warning(f"Knowledge brain not found at {path}")
            return
        try:
            text = path.read_text(encoding="utf-8")
            atoms = self._parse_brain_markdown(text)
            logger.info(f"Loaded {len(atoms)} atoms from knowledge brain")
            self.add_documents([a["content"] for a in atoms], [a["metadata"] for a in atoms])
        except Exception as e:
            logger.error(f"Knowledge brain load failed: {e}")

    @staticmethod
    def _parse_brain_markdown(text: str) -> list[dict[str, Any]]:
        """Parse markdown atoms like ### K-101 | Title ... into structured docs."""
        import re
        pattern = re.compile(r"###\s+([A-Z]-\d{3})\s*\|\s*(.+?)\n(.+?)(?=###\s+[A-Z]-\d{3}|\Z)", re.DOTALL)
        atoms: list[dict[str, Any]] = []
        for m in pattern.finditer(text):
            atom_id = m.group(1)
            title = m.group(2).strip()
            body = m.group(3).strip()
            atoms.append({
                "content": f"{title}\n{body}",
                "metadata": {
                    "atom_id": atom_id,
                    "source": "SECOND-KNOWLEDGE-BRAIN.md",
                    "source_type": "knowledge_atom",
                },
            })
        return atoms

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------

    def _persist_bm25(self) -> None:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        with open(self.persist_dir / "bm25_index.pkl", "wb") as f:
            pickle.dump(self._bm25, f)
        with open(self.persist_dir / "bm25_corpus.json", "w", encoding="utf-8") as f:
            json.dump({"texts": self._corpus_texts, "metas": self._corpus_metas}, f, ensure_ascii=False)

    def persist(self) -> None:
        """Persist any pending state."""
        self._persist_bm25()
        if CHROMA_AVAILABLE and self._chroma_client:
            try:
                self._chroma_client.persist()
            except Exception as e:
                logger.warning(f"ChromaDB persist failed: {e}")