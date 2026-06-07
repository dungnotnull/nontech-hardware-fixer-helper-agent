"""Text chunking strategies for repair manuals and knowledge atoms."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger


class TextChunker:
    """Chunk documents preserving step-level boundaries and model applicability."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        by_steps: bool = True,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.by_steps = by_steps
        logger.info(f"TextChunker: size={chunk_size}, overlap={chunk_overlap}, by_steps={by_steps}")

    def chunk_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Chunk text into pieces with metadata."""
        meta = metadata or {}
        if self.by_steps:
            return self._chunk_by_steps(text, meta)
        return self._chunk_by_tokens(text, meta)

    def _chunk_by_steps(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Split on numbered steps first, then token-size boundaries."""
        # Regex for numbered steps like "1. ", "Step 1:", etc.
        step_pattern = re.compile(r"(?:\n\s*(?:\d+[\.\)]\s+|Step\s+\d+[\.:]\s+))", re.IGNORECASE)
        parts = step_pattern.split(text)
        if len(parts) <= 1:
            return self._chunk_by_tokens(text, metadata)

        chunks: list[dict[str, Any]] = []
        current_chunk = ""
        step_num = 0
        for part in parts:
            if not part.strip():
                continue
            step_num += 1
            candidate = current_chunk + "\n" + part if current_chunk else part
            if len(candidate.split()) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "metadata": {**metadata, "chunk_type": "step_group", "step_range": step_num},
                    })
                current_chunk = part
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {**metadata, "chunk_type": "step_group", "step_range": step_num},
            })
        return chunks

    def _chunk_by_tokens(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Naive token-based sliding window chunking."""
        words = text.split()
        chunks: list[dict[str, Any]] = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunks.append({
                "text": " ".join(chunk_words),
                "metadata": {**metadata, "chunk_type": "sliding_window", "chunk_index": len(chunks)},
            })
            start = end - self.chunk_overlap if end < len(words) else end
        return chunks

    def chunk_pdf_pages(self, pages: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Chunk extracted PDF pages."""
        all_chunks: list[dict[str, Any]] = []
        for page in pages:
            page_meta = {**(metadata or {}), "page": page.get("page_num", 0)}
            chunks = self.chunk_text(page.get("text", ""), page_meta)
            all_chunks.extend(chunks)
        return all_chunks