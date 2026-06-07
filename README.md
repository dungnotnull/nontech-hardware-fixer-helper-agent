<h1 align="center">FixerAgent </h1>

<p align="center">
  <b>AI-Powered Home Appliance Repair Assistant for Non-Technical Users</b><br/>
  Snap a photo. Get precise, illustrated, safety-rated repair instructions in seconds.
</p>

<p align="center">
  <a href="https://github.com/dungnotnull/nontech-hardware-fixer-helper-agent/actions/workflows/ci.yml">
    <img src="https://github.com/dungnotnull/nontech-hardware-fixer-helper-agent/actions/workflows/ci.yml/badge.svg" alt="CI" />
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+" />
  </a>
  <a href="https://nextjs.org/">
    <img src="https://img.shields.io/badge/Next.js-14-black" alt="Next.js 14" />
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img src="https://img.shields.io/badge/FastAPI-0.111+-teal" alt="FastAPI" />
  </a>
</p>

---

## Table of Contents

- [Safety Notice](#safety-notice)
- [What is FixerAgent](#what-is-fixeragent)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [CLI Usage](#cli-usage)
- [Safety Architecture](#safety-architecture)
- [Development Roadmap](#development-roadmap)
- [Contributing](#contributing)
- [Legal](#legal)
- [License](#license)

---

## Safety Notice

**FixerAgent is an informational AI tool, NOT a substitute for professional repair services.**

- **Red / Professional Only** repairs (mains voltage, gas lines, microwave internals, refrigerant, CRT) must **never** be attempted by end users.
- Always **unplug devices** before any physical intervention.
- If unsure about any step, **stop and contact a certified technician**.

Read the full [Liability Disclaimer](docs/legal/LIABILITY_DISCLAIMER.md) before use.

---

## What is FixerAgent

When household devices break, most people face two bad options:

1. **Call a technician** - expensive ($50-200+), long wait, often unnecessary for simple fixes
2. **Search YouTube/Google** - overwhelming results, wrong device variant, no personalization, no visual diagnosis

**FixerAgent fills the gap.** It takes a photo of your broken device and delivers precise, illustrated, safety-rated DIY repair instructions tailored to your exact model. It identifies the device via computer vision, retrieves the correct procedure from manufacturer manuals, and guides you step-by-step - all in under 30 seconds.

### How It Works

```
User Photo + Description
        |
        v
[Vision Analyzer] -- Claude / GPT-4o / Gemini
        |
        v
[Device Identification] -- brand, model, error codes
        |
        v
[Safety Assessor] -- auto-escalation for hazards
        |
        v
[RAG Engine] -- hybrid dense + sparse + rerank
        |
        v
[Repair Guide Generator] -- LLM-powered step-by-step
        |
        v
Illustrated Repair Guide + Safety Tier Badge
```

---

## Features

### 1. Visual Diagnosis
- Upload a photo of any broken appliance or error screen
- Multi-provider vision AI: Claude, GPT-4o, Gemini, or local Ollama
- OCR extracts model numbers and error codes automatically
- Image preprocessing: resize, autocontrast, format normalization

### 2. Hybrid RAG Knowledge Retrieval
- **Dense retrieval**: BAAI/bge-large-en-v1.5 embeddings via ChromaDB
- **Sparse retrieval**: BM25Okapi keyword index with persistence
- **Reranking**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **Fusion**: Reciprocal Rank Fusion (RRF) for best-of-both-worlds results
- Sources: manufacturer manuals, iFixit guides, RepairClinic symptoms, arXiv research

### 3. Safety-First Repair Guides
- Every guide carries a **Tier Badge**:
  - Green / DIY Easy - simple reset, cleaning, user error
  - Yellow / DIY Moderate - basic tools, moderate skill
  - Orange / DIY Advanced - confident DIYer, specific tools
  - Red / Professional Only - **never attempt, call a technician**
- Auto-escalation for microwave capacitors, CRT lethal charge, gas lines, refrigerant
- Safety warnings at the **top** of every guide, never buried

### 4. Self-Improving Knowledge Base
- **Weekly auto-crawl** from arXiv (research papers), iFixit (repair guides), manufacturer RSS bulletins, RepairClinic (symptoms)
- Relevance filtering via embedding cosine similarity
- SHA256 deduplication against existing corpus
- Auto-append new knowledge atoms to SECOND-KNOWLEDGE-BRAIN.md

### 5. Production Backend
- FastAPI with async endpoints
- Rate limiting (Redis sliding window + memory fallback)
- Admin API key auth for knowledge management
- Prometheus metrics: latency, feedback, KB size, repair tiers
- Docker multi-stage + Docker Compose (app + ChromaDB + Redis)

### 6. Modern Web Frontend
- Next.js 14 + TypeScript + Tailwind CSS
- Drag-and-drop image upload with camera support
- Real-time diagnosis progress animation
- Responsive repair guide renderer with tier badges, step cards, caution notes
- Feedback collection: fixed / partial / failed with optional notes

### 7. Outcome Prediction
- XGBoost classifier predicts repair success probability
- Features: device category, fault type, safety tier, user skill, error code presence
- Heuristic fallback when model is unavailable
- Feedback-driven continuous improvement

---

## System Architecture

```
+------------------------------------------------------------------+
|                         USER INTERFACE                            |
|           Web App (Next.js) / Mobile / CLI (Click)               |
+------------------------+------------------+----------------------+
                         |                  |
                         v                  v
              +------------------+  +------------------+
              |  Upload Image    |  |  Text Description |
              +--------+---------+  +--------+---------+
                       |                     |
                       +----------+----------+
                                  |
                                  v
+------------------------------------------------------------------+
|                    FIXERAGENT ORCHESTRATION                       |
|              LangGraph State Machine Pipeline                     |
|  diagnose -> safety_check -> retrieve -> generate -> feedback     |
+---------+------------------+------------------+-----------------+
          |                  |                  |
          v                  v                  v
+---------+------+  +--------+--------+  +-----+----------+
| Vision Module  |  |   RAG Engine    |  | LLM Router     |
| Claude/GPT/Gem|  | ChromaDB + BM25 |  | Claude/OpenAI  |
| TrOCR + OCR    |  | + Cross-Encoder |  | Gemini/Local   |
+----------------+  +--------+--------+  +----------------+
                             |
                             v
+------------------------------------------------------------------+
|                      KNOWLEDGE BASE                               |
|  SECOND-KNOWLEDGE-BRAIN.md | Manufacturer PDFs | iFixit/Research |
+------------------------------------------------------------------+
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Language | Python 3.11+, TypeScript | Core + Frontend |
| Agent Framework | LangGraph-style state machine | Diagnosis pipeline |
| Vision API | Claude / GPT-4o / Gemini / Ollama | Image analysis |
| OCR | pytesseract / TrOCR | Model number extraction |
| Vector DB | ChromaDB -> Qdrant | Semantic search |
| Embeddings | BAAI/bge-large-en-v1.5 | Document vectors |
| Sparse Retrieval | rank_bm25 | Keyword search |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Result refinement |
| LLM Router | httpx | Unified multi-provider API |
| API Framework | FastAPI + uvicorn | REST backend |
| Frontend | Next.js 14 + Tailwind CSS | Web UI |
| Cache / Broker | Redis | Rate limiting + Celery |
| Task Queue | Celery + APScheduler | Async jobs + weekly crawl |
| Monitoring | Prometheus + Loguru | Metrics + logging |
| Testing | pytest + pytest-asyncio | Unit + integration tests |
| Container | Docker + Docker Compose | Deployment |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- Node.js 18+ (for frontend)
- `uv` (recommended) or `pip`

### 1. Clone and Install

```bash
git clone https://github.com/dungnotnull/nontech-hardware-fixer-helper-agent.git
cd nontech-hardware-fixer-agent

# Install Python dependencies
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys:
# LLM_API_KEY=sk-...
# VISION_API_KEY=sk-...
```

### 3. Start Infrastructure

```bash
docker compose up -d
# Starts: FastAPI app, ChromaDB, Redis
```

### 4. Seed Knowledge Base

```bash
# Load curated knowledge brain
fixer brain_reload

# Ingest PDF manuals (place them in data/manuals/)
fixer ingest --directory ./data/manuals
```

### 5. Run CLI Diagnosis

```bash
fixer diagnose --image ./photo.jpg --describe "Red light blinking 4 times"
```

### 6. Or Start the Web Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | Public | Service health check |
| POST | `/diagnose` | Public | Multipart image upload + description |
| POST | `/diagnose/json` | Public | Base64 image JSON payload |
| POST | `/feedback` | Public | Submit repair outcome |
| GET | `/guide/{session_id}` | Public | Retrieve cached guide |
| GET | `/devices` | Public | List supported categories/brands |
| POST | `/knowledge/crawl` | Admin | Trigger knowledge crawl |
| POST | `/knowledge/ingest` | Admin | Batch PDF upload |
| GET | `/knowledge/status` | Public | KB size and crawl status |

### Example: Diagnose with curl

```bash
curl -X POST "http://localhost:8000/diagnose" \
  -F "image=@photo.jpg" \
  -F "description=Red light blinking 4 times" \
  -F "llm_provider=claude" \
  -F "llm_api_key=$CLAUDE_API_KEY"
```

---

## CLI Usage

```bash
# Diagnosis
fixer diagnose --image photo.jpg --describe "Won't turn on"

# JSON output for scripting
fixer diagnose --image photo.jpg --describe "..." --json-out

# Submit feedback
fixer feedback --session abc123 --outcome fixed --notes "Took 10 minutes"

# Ingest manuals
fixer ingest --directory ./data/manuals/
fixer ingest ./manuals/HP_LaserJet.pdf ./manuals/Canon_PIXMA.pdf

# Reload knowledge brain
fixer brain_reload

# Check system health
fixer health
```

---

## Safety Architecture

Safety is the **highest priority** in FixerAgent. The system enforces multiple layers of protection:

### Tier Classification System

| Tier | Badge | Who Can Do It | Examples |
|------|-------|--------------|----------|
| 1 | Green / DIY Easy | Any user | Wi-Fi reset, filter cleaning, drain unclogging |
| 2 | Yellow / DIY Moderate | Handy user | Replacing fuses, ink cartridges, door seals |
| 3 | Orange / DIY Advanced | Confident DIYer | Replacing heating elements, belts, fans |
| 4 | Red / Professional Only | Certified technician | Mains wiring, refrigerant, structural, microwave internals |

### Auto-Escalation Rules

The following **always** escalate to Professional Only, regardless of fault type:

- **Microwave / microwave oven** - internal capacitors hold 2000V+ after unplugging
- **CRT monitors / TVs** - can retain 25000V+ lethal charge for years
- **Gas appliances** - gas leaks can cause explosions or carbon monoxide poisoning
- **HVAC / furnaces** - refrigerant and combustion hazards
- **Mains voltage repairs** - anything requiring opening a device connected to >50V AC

### Confidence Gates

| Device ID Confidence | Action |
|---------------------|--------|
| >= 85% | Proceed with diagnosis |
| 60-84% | Ask clarifying question |
| < 60% | Request better image or model number |

### Knowledge Source Priority

1. SECOND-KNOWLEDGE-BRAIN.md (curated, verified)
2. Official manufacturer manuals (RAG corpus)
3. iFixit / verified community sources
4. External LLM inference (always flagged as "estimated")

---

## Development Roadmap

All phases implemented and production-ready:

| Phase | Focus | Status |
|-------|-------|--------|
| **0 - Init & Skeleton** | Monorepo, schemas, Docker, logging | Done |
| **1 - Foundation & MVP** | CLI agent: photo -> repair guide | Done |
| **2 - Full Intelligence** | Auto-crawl, FastAPI, hybrid RAG | Done |
| **3 - Scale & Learn** | Feedback loop, XGBoost, Qdrant, Redis | Done |
| **4 - Product** | Next.js frontend, legal docs, OSS hygiene | Done |

See [PROJECT-DEVELOPMENT-PHASE-TRACKING.md](PROJECT-DEVELOPMENT-PHASE-TRACKING.md) for full sprint breakdown.

---

## Project Structure

```
nontech-hardware-fixer-agent/
|-- src/fixeragent/           # Core Python backend
|   |-- agents/               # Orchestration layer
|   |   |-- fixer_agent.py    # Main diagnosis pipeline
|   |-- api/                  # FastAPI backend
|   |   |-- main.py           # All endpoints + lifespan
|   |   |-- auth.py           # API key admin auth
|   |   |-- rate_limit.py     # Redis sliding-window rate limiter
|   |-- config/               # Settings + logging
|   |   |-- settings.py       # pydantic-settings loader
|   |   |-- logging_config.py # Loguru configuration
|   |-- models/               # Pydantic v2 schemas
|   |   |-- schemas.py        # DiagnosticPayload, RepairGuide, etc.
|   |-- tools/                # Core tool modules
|   |   |-- llm_router.py     # Unified multi-provider LLM API
|   |   |-- vision_analyzer.py# VLM + OCR + preprocessing
|   |   |-- rag_engine.py     # Hybrid dense/sparse/rerank retrieval
|   |   |-- safety_assessor.py# Rule-based tier classification
|   |   |-- repair_generator.py# LLM guide generation
|   |   |-- chunker.py        # Step-level + sliding-window chunking
|   |   |-- pdf_ingestor.py   # PyMuPDF + pdfplumber ingestion
|   |   |-- arxiv_crawler.py  # Research paper crawler
|   |   |-- ifixit_client.py  # Repair guide API client
|   |   |-- rss_scraper.py    # Manufacturer bulletin scraper
|   |   |-- repairclinic_scraper.py # Playwright symptom scraper
|   |   |-- feedback_analytics.py   # Success rate analytics
|   |   |-- outcome_predictor.py    # XGBoost repair success predictor
|   |   |-- qdrant_migration.py     # ChromaDB -> Qdrant migration
|   |   |-- redis_cache.py    # TTL caching layer
|   |   |-- metrics.py         # Prometheus instrumentation
|   |-- celery_config.py      # Celery + Redis broker
|   |-- cli.py                # Click CLI entry point
|   |-- tasks.py              # Async background tasks
|-- frontend/                 # Next.js 14 web app
|   |-- app/                  # App router pages
|   |   |-- page.tsx          # Landing page
|   |   |-- diagnose/page.tsx # Diagnosis flow
|   |-- components/           # React components
|   |   |-- ImageUpload.tsx   # Drag-drop image upload
|   |   |-- DiagnosisProgress.tsx # Animated step progress
|   |   |-- RepairGuide.tsx   # Guide renderer with tier badges
|   |   |-- FeedbackForm.tsx  # Outcome feedback UI
|   |-- lib/api.ts            # Axios API client
|-- tests/                    # pytest suite
|-- scripts/                  # Knowledge updater, crawlers
|   |-- knowledge_updater.py  # Weekly crawl pipeline
|-- data/                     # Runtime data
|   |-- manuals/              # PDF manuals by brand
|   |-- corpus/               # Embeddings + BM25 index
|   |-- knowledge_brain/      # SECOND-KNOWLEDGE-BRAIN.md
|   |-- device_catalog/       # devices.json
|   |-- feedback_logs/        # outcomes.jsonl
|   |-- crawl_cache/          # Crawl state tracking
|-- docs/
|   |-- legal/
|   |   |-- TOS.md            # Terms of Service
|   |   |-- LIABILITY_DISCLAIMER.md # Critical safety disclaimer
|-- .github/
|   |-- workflows/ci.yml      # GitHub Actions CI
|   |-- ISSUE_TEMPLATE/       # Bug report template
|   |-- pull_request_template.md
|-- CONTRIBUTING.md           # Contribution guidelines
|-- SECURITY.md               # Vulnerability disclosure
|-- CHANGELOG.md              # Release history
|-- PROJECT-detail.md         # Full technical specification
|-- PROJECT-DEVELOPMENT-PHASE-TRACKING.md # Roadmap
|-- SECOND-KNOWLEDGE-BRAIN.md # Curated knowledge base
|-- pyproject.toml            # Dependencies + build
|-- docker-compose.yml        # App + ChromaDB + Redis
|-- Dockerfile                # Multi-stage build
|-- .env.example              # Configuration template
|-- LICENSE                   # MIT License
|-- README.md                 # This file
```

---

## Contributing

We welcome bug reports, feature requests, and pull requests!

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup with `uv` and Docker
- Coding standards (Python 3.11+, Pydantic v2, Loguru, type hints)
- Safety-critical review process for tier classification changes
- Conventional Commits format

For security vulnerabilities, see [SECURITY.md](SECURITY.md) for responsible disclosure.

---

## Legal

By using FixerAgent, you agree to:
- [Terms of Service](docs/legal/TOS.md)
- [Liability Disclaimer](docs/legal/LIABILITY_DISCLAIMER.md)

These documents contain critical safety information. **Read them before attempting any repair.**

---

## License

FixerAgent is released under the [MIT License](LICENSE).

```
MIT License

Copyright (c) 2026 FixerAgent Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<p align="center">
Built with care for non-technical homeowners everywhere.<br/>
If it is broken, FixerAgent helps you fix it - safely.
</p>
