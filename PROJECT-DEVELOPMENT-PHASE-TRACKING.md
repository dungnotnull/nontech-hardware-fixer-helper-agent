# PROJECT-DEVELOPMENT-PHASE-TRACKING.md

> Development Roadmap & Sprint Tracker
> Project: nontech-hardware-fixer-agent
> Version: 0.1.0 | Last Updated: 2026-06-07

---

## Roadmap Overview

```
Phase 0: Init & Skeleton      [DONE]  [================]  Foundation Complete
Phase 1: Foundation & MVP       [DONE]  [================]  CLI Agent Working
Phase 2: Full Intelligence      [DONE]  [================]  FastAPI + Crawlers
Phase 3: Scale & Learn          [DONE]  [================]  Feedback + XGBoost + Infra
Phase 4: Product              [DONE]  [================]  Next.js Frontend + Launch Prep
```

---

## Phase 0: Project Initialization & Skeleton (Complete)

**Goal**: Complete project infrastructure, monorepo, dependencies, schemas, Docker, logging, and documentation so development can begin immediately.

**Success Criteria**:
- [x] All project files exist and are version-controlled
- [x] `pyproject.toml` installable with `uv pip install -e ".[dev]"`
- [x] Docker Compose brings up app + ChromaDB + Redis
- [x] Pydantic schemas cover all core data models
- [x] `.env.example` documents every required configuration key
- [x] Unit tests exist for schema validation and safety logic
- [x] README explains project structure and quick start

**Deliverables**:
- Monorepo: `src/`, `tests/`, `config/`, `data/`, `scripts/`, `docs/`, `frontend/`
- `pyproject.toml` with 35+ dependencies and dev extras (pytest, black, ruff, mypy)
- `Dockerfile` (multi-stage: base -> dev -> prod) + `docker-compose.yml` (app + ChromaDB + Redis)
- `pydantic-settings` config loader with `@lru_cache` singleton
- Loguru logging with stderr + rotating file sink (10 MB / 30-day retention)
- `README.md`, `LICENSE` (MIT), `.gitignore`
- Data hierarchy seeded with `devices.json` catalog

---

## Phase 1: Foundation & MVP (Complete)

**Goal**: A working CLI-based agent that can take an image + description and return a repair guide.

**Success Criteria**:
- [x] Vision module integrates Claude, GPT-4o, Gemini, and local/Ollama vision APIs
- [x] TrOCR / pytesseract for model number and error code extraction
- [x] Image preprocessing pipeline (resize, autocontrast, JPEG normalization)
- [x] RAG engine with real ChromaDB + BAAI/bge-large-en-v1.5 embeddings
- [x] BM25 sparse index via `rank_bm25` with persistence
- [x] Cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`)
- [x] Reciprocal Rank Fusion (RRF) for dense + sparse fusion
- [x] Safety assessor with rule-based tier classification + auto-escalation for microwave/CRT/gas
- [x] Repair guide generator with real LLM-powered JSON generation + markdown renderer
- [x] LangGraph-style state machine orchestration (vision -> safety -> RAG -> generation)
- [x] LLM Router with provider switching and fallback chain
- [x] Click CLI: `fixer diagnose --image --describe`, `fixer feedback`, `fixer ingest`, `fixer brain_reload`
- [x] PDF ingestion pipeline (`PyMuPDF` + `pdfplumber` + `TextChunker`)
- [x] Text chunker with step-level and sliding-window strategies

**Key Files**:
- `src/fixeragent/tools/llm_router.py` -- unified Claude/OpenAI/Gemini/local chat + vision
- `src/fixeragent/tools/vision_analyzer.py` -- VLM + OCR + preprocessing
- `src/fixeragent/tools/rag_engine.py` -- hybrid dense/sparse/rerank retrieval
- `src/fixeragent/tools/safety_assessor.py` -- tier classification with hard safety rules
- `src/fixeragent/tools/repair_generator.py` -- LLM guide generation with fallback
- `src/fixeragent/agents/fixer_agent.py` -- orchestration pipeline
- `src/fixeragent/cli.py` -- Click CLI entry point
- `src/fixeragent/tools/pdf_ingestor.py` + `chunker.py` -- manual ingestion

---

## Phase 2: Full Intelligence Pipeline (Complete)

**Goal**: Production-quality AI pipeline with auto-crawling knowledge update and FastAPI backend.

**Success Criteria**:
- [x] arXiv crawler (`aiohttp` + `feedparser`) for appliance diagnosis research papers
- [x] iFixit API client for repair guide crawling
- [x] Manufacturer RSS bulletin scraper (HP, Canon, Samsung, Bosch, Philips)
- [x] RepairClinic scraper (`Playwright` async) for symptom guides
- [x] Knowledge updater pipeline: crawl -> relevance filter (embedding cosine > 0.7) -> deduplicate (SHA256) -> index + append to BRAIN.md
- [x] FastAPI backend with all endpoints:
  - `POST /diagnose` (multipart image upload)
  - `POST /diagnose/json` (base64 JSON)
  - `POST /feedback`
  - `GET /guide/{session_id}`
  - `POST /knowledge/crawl` (admin, API key auth)
  - `POST /knowledge/ingest` (admin, PDF batch upload)
  - `GET /knowledge/status`
  - `GET /devices`
  - `GET /health`
- [x] CORS middleware, rate limiting (Redis sliding window + in-memory fallback)
- [x] Admin API key auth (`Authorization: Bearer ...`)
- [x] Global exception handler
- [x] APScheduler-ready Celery tasks for async diagnosis and weekly crawl

**Key Files**:
- `src/fixeragent/tools/arxiv_crawler.py`
- `src/fixeragent/tools/ifixit_client.py`
- `src/fixeragent/tools/rss_scraper.py`
- `src/fixeragent/tools/repairclinic_scraper.py`
- `scripts/knowledge_updater.py` -- orchestrated pipeline
- `src/fixeragent/api/main.py` -- FastAPI app with lifespan + all endpoints
- `src/fixeragent/api/auth.py` + `rate_limit.py`
- `src/fixeragent/celery_config.py` + `tasks.py`

---

## Phase 3: Self-Improvement & Scale (Complete)

**Goal**: The agent measurably improves from feedback and new knowledge over time.

**Success Criteria**:
- [x] Feedback analytics pipeline: parse `outcomes.jsonl`, compute success rates
- [x] Weak category identification (success rate < 60%) with breakdown by fault type
- [x] Monthly performance report generator
- [x] XGBoost outcome predictor with full feature engineering (tier, fault_type, device_category, error_code presence, user skill)
- [x] Heuristic fallback predictor when model is unavailable
- [x] Train + save / load XGBoost model pipeline
- [x] Qdrant migration module: zero-downtime ChromaDB -> Qdrant collection copy
- [x] Qdrant hybrid search interface
- [x] Redis cache helper with TTL for frequent queries
- [x] Celery async task definitions: `async_diagnose`, `weekly_knowledge_crawl`, `train_outcome_predictor`
- [x] Prometheus metrics: diagnosis latency histogram, feedback counters, KB size gauge, repair tier counter

**Key Files**:
- `src/fixeragent/tools/feedback_analytics.py`
- `src/fixeragent/tools/outcome_predictor.py`
- `src/fixeragent/tools/qdrant_migration.py`
- `src/fixeragent/tools/redis_cache.py`
- `src/fixeragent/tools/metrics.py`

---

## Phase 4: Product (Complete)

**Goal**: Consumer-facing web application ready for deployment.

**Success Criteria**:
- [x] Next.js 14 app-router frontend with TypeScript + Tailwind CSS
- [x] Home page with feature cards and navigation
- [x] Diagnosis page: image upload (drag & drop), text description, device hint
- [x] Real-time diagnosis progress UI with animated step list
- [x] Repair guide renderer: tier badge, tools/parts list, step-by-step cards, caution notes, test procedure
- [x] Safety escalation UI (red card for tier-4 professional-only repairs)
- [x] Feedback collection UI: fixed / partial / failed buttons + notes
- [x] API client layer (`axios`) with `multipart/form-data` upload
- [x] Responsive design (mobile-first with Tailwind)
- [x] Standalone Docker output config (`output: 'standalone'`)
- [x] TOS / liability disclaimer references in app copy
- [x] SEO-ready metadata and semantic HTML

**Key Files**:
- `frontend/package.json`, `tsconfig.json`, `next.config.js`, `tailwind.config.ts`
- `frontend/app/layout.tsx`, `page.tsx`, `diagnose/page.tsx`
- `frontend/components/ImageUpload.tsx`, `DiagnosisProgress.tsx`, `RepairGuide.tsx`, `FeedbackForm.tsx`
- `frontend/lib/api.ts`

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| [x] DONE | Completed and implemented |
| [ ] TODO | Not started |
| [-] BLOCKED | Blocked by dependency |

---

## Key Metrics Dashboard

| Metric | Target | Status |
|--------|--------|--------|
| Device ID Accuracy | >= 80% MVP / >= 88% Phase 2 / >= 92% Phase 3 | Code ready |
| Retrieval NDCG@5 | >= 0.75 / >= 0.82 / >= 0.87 | Hybrid RAG implemented |
| Repair Success Rate | Baseline -> +5% | Feedback loop ready |
| Avg Response Time | < 30s MVP / < 15s Phase 2 / < 10s Phase 3 | Async + cache ready |
| Knowledge Base Size | 200 -> 500 -> 1000+ | Crawler pipeline ready |
| Device Categories | 5 -> 15 -> 30+ | Catalog seeded, extensible |

---

## Technical Debt & Known Risks Log

| Item | Risk Level | Status | Notes |
|------|------------|--------|-------|
| Copyright of scraped manuals | Medium | Mitigated | Only index open/public manuals; respect robots.txt |
| Vision API cost at scale | High | Mitigated | Cache by image hash; local VLM option in router |
| LLM hallucination in steps | High | Mitigated | Ground all steps in retrieved text; JSON schema enforced |
| LED pattern detection edge cases | Low | Accepted | Rule-based sufficient for MVP; Phase 2 ML reserved |
| SECOND-KNOWLEDGE-BRAIN conflicts | Medium | Mitigated | Deduplication via SHA256 hash on ingestion |
| Missing dependency at runtime | Low | Mitigated | Graceful degradation with try/except + logger warnings |

---

*This document is the single source of truth for development progress.*
*All phases 0-4 are implemented and marked DONE.*