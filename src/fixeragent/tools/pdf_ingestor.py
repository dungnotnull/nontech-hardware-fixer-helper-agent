"""PDF manual ingestion pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from fixeragent.tools.chunker import TextChunker

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available; PDF ingestion disabled")


try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except Exception:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available; table extraction disabled")


class PDFIngestor:
    """Extract text and tables from manufacturer PDF manuals."""

    def __init__(self, chunker: TextChunker | None = None) -> None:
        self.chunker = chunker or TextChunker()

    def ingest(self, pdf_path: str | Path, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Extract and chunk a single PDF. Returns list of chunks with metadata."""
        pdf_path = Path(pdf_path)
        logger.info(f"Ingesting PDF: {pdf_path}")
        pages = self._extract_pages(pdf_path)
        meta = metadata or {
            "source_file": pdf_path.name,
            "source_type": "pdf_manual",
        }
        chunks = self.chunker.chunk_pdf_pages(pages, meta)
        logger.info(f"PDF ingested: {len(pages)} pages → {len(chunks)} chunks")
        return chunks

    def _extract_pages(self, pdf_path: Path) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(str(pdf_path))
                for i, page in enumerate(doc):
                    text = page.get_text()
                    pages.append({"page_num": i + 1, "text": text})
                doc.close()
                return pages
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}")
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(str(pdf_path)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        pages.append({"page_num": i + 1, "text": text})
                return pages
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed: {e}")
        logger.error(f"No PDF backend available for {pdf_path}")
        return []

    def extract_tables(self, pdf_path: str | Path, page_numbers: list[int] | None = None) -> list[list[list[str]]]:
        """Extract tables from PDF pages using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            logger.error("pdfplumber not available for table extraction")
            return []
        tables: list[list[list[str]]] = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                pages_to_process = page_numbers or range(len(pdf.pages))
                for i in pages_to_process:
                    page = pdf.pages[i]
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
            logger.info(f"Extracted {len(tables)} tables from {pdf_path}")
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        return tables