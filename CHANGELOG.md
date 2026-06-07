# Changelog

All notable changes to FixerAgent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-06-07

### Added
- Full project skeleton with monorepo structure (`src/`, `tests/`, `frontend/`, `docs/`)
- Pydantic v2 schemas: `DiagnosticPayload`, `RepairGuide`, `SafetyAssessment`, `FeedbackOutcome`, `KnowledgeAtom`, `LLMConfig`, `CrawlStatus`, `RetrievalChunk`, `DiagnosisRequest`, `DiagnosisResponse`
- LLM Router with unified API for Claude, OpenAI, Gemini, and local/Ollama (chat + vision)
- Vision Analyzer: image preprocessing (resize, autocontrast), VLM analysis via LLM Router, OCR via pytesseract/TrOCR, model number / error code extraction
- RAG Engine: ChromaDB + BAAI/bge-large-en-v1.5 embeddings, BM25 sparse index, cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`), Reciprocal Rank Fusion
- Safety Assessor: rule-based tier classification (DIY Easy → Professional Only), auto-escalation for microwave/CRT/gas/mains voltage
- Repair Guide Generator: LLM-powered JSON step generation with markdown renderer and fallback extraction from top chunk
- FixerAgent orchestration: LangGraph-style state machine (vision → safety → RAG → guide generation)
- PDF Ingestor (`PyMuPDF` + `pdfplumber`) and `TextChunker` (step-level + sliding-window chunking)
- Click CLI: `diagnose`, `feedback`, `ingest`, `brain_reload`, `health`
- FastAPI backend: `/diagnose` (multipart + base64), `/feedback`, `/guide/{id}`, `/knowledge/crawl` (admin), `/knowledge/ingest` (admin), `/knowledge/status`, `/devices`, `/health`
- API key auth for admin endpoints, Redis sliding-window rate limiter, CORS, global exception handler
- Knowledge crawlers: arXiv (`aiohttp` + `feedparser`), iFixit API, manufacturer RSS bulletins, RepairClinic (`playwright`)
- Knowledge Updater pipeline: crawl → relevance filter (embedding cosine > 0.7) → SHA256 deduplicate → index + auto-append to `SECOND-KNOWLEDGE-BRAIN.md`
- Feedback Analytics: success rate computation, weak category identification, monthly report generator
- Outcome Predictor: XGBoost classifier with feature engineering + heuristic fallback
- Qdrant migration module: zero-downtime ChromaDB → Qdrant collection copy
- Redis cache helper with TTL
- Celery tasks: `async_diagnose`, `weekly_knowledge_crawl`, `train_outcome_predictor`
- Prometheus metrics: diagnosis latency, feedback counters, KB size gauge, repair tier counter
- Next.js 14 frontend: image upload (drag-drop), diagnosis progress, repair guide renderer, feedback UI
- Docker multi-stage `Dockerfile` + `docker-compose.yml` (app + ChromaDB + Redis)
- `pyproject.toml` with 35+ dependencies and dev extras
- Loguru logging with stderr + rotating file sinks
- MIT License, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`
- GitHub Actions CI: Python lint/test/format, Docker health check, frontend build
- GitHub templates: bug report, pull request
- Legal docs: `TOS.md`, `Liability Disclaimer` with explicit Tier-4 repair prohibitions

### Security
- Admin endpoints protected by API key bearer auth
- Rate limiting on `/diagnose` endpoints
- User images are not persisted beyond active session
- Safety escalation for mains voltage, gas, refrigerant, microwave capacitors, CRT charge

---

## [Unreleased]

Planned for future releases:
- WebSocket real-time diagnosis progress
- Mobile app (React Native / Capacitor)
- OAuth2 user accounts and saved repair history
- Parts sourcing integration (Amazon / RepairClinic affiliate APIs)
- Multi-language support (i18n)
- A/B testing framework for RAG retrieval tuning
- Synthetic training data generator for outcome predictor
