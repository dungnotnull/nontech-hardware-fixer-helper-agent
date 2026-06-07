# PROJECT-detail.md — nontech-hardware-fixer-agent

> **Full Technical & Product Specification**
> Version: 0.1.0 | Status: Planning

---

## 1. Project Overview

### Name
`nontech-hardware-fixer-agent` — Home Appliance Repair Assistant

### Problem Statement
When household devices break (printers, microwaves, Wi-Fi routers, faucets, washing machines), most people face two bad options:
1. **Call a technician** — expensive ($50–200+), long wait, often unnecessary for simple fixes
2. **Search YouTube/Google** — overwhelming results, wrong device variant, no personalization, no visual diagnosis

**The gap**: No existing tool takes a *photo of your broken device* and gives you *precise, illustrated, step-by-step repair instructions* tailored to your exact model.

### Solution
An agentic AI system that:
1. Accepts a photo or video of the broken device/symptom
2. Identifies the exact device and fault using computer vision
3. Retrieves the correct repair procedure from manufacturer manuals and curated knowledge
4. Delivers a clear, illustrated, safety-rated DIY repair guide
5. Learns continuously from new research and user feedback

### Target Users
- Primary: Non-technical homeowners (25–65 years old)
- Secondary: Small appliance repair shops, property managers, landlords
- Tertiary: Home insurance companies (claims triage)

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│          Web App / Mobile App / CLI (Phase 1: CLI)          │
└─────────────────────┬───────────────────────────────────────┘
                      │  Image / Video / Text input
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                       │
│                   FixerAgent (LangChain /                    │
│                   LlamaIndex Agentic Loop)                   │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐
│  VISION  │  │  RAG ENGINE  │  │   EXTERNAL LLM ROUTER    │
│  MODULE  │  │              │  │                          │
│          │  │ Vector DB    │  │  Claude / GPT / Gemini   │
│ GPT-4o   │  │ (ChromaDB /  │  │  (user-configured)       │
│ Vision   │  │  Qdrant)     │  │                          │
│    or    │  │              │  │  Fallback: local model   │
│ Claude   │  │ Manual Corpus│  │                          │
│ Vision   │  │ + Knowledge  │  │                          │
│    or    │  │   Brain      │  │                          │
│ Gemini   │  └──────────────┘  └──────────────────────────┘
│ Vision   │          │
└──────────┘          │
       │              ▼
       │    ┌──────────────────┐
       │    │  KNOWLEDGE BASE  │
       │    │                  │
       │    │ SECOND-KNOWLEDGE │
       │    │ -BRAIN.md        │
       │    │                  │
       │    │ Manufacturer     │
       │    │ Manuals (PDF)    │
       │    │                  │
       │    │ iFixit / RepairDB│
       │    └──────────────────┘
       │              │
       └──────┬───────┘
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    REPAIR GUIDE GENERATOR                    │
│     Safety Assessment → Step Generation → Image Retrieval   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FEEDBACK & LEARNING LOOP                  │
│   User Rating → Outcome Log → Knowledge Update Pipeline     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 Vision Module

**Purpose**: Extract structured diagnostic information from images/video frames

**Primary Models** (in priority order):
| Model | Use Case | Source |
|---|---|---|
| `GPT-4o` or `claude-opus-4-6` | Primary vision analysis (via user API) | External API |
| `google/owlvit-base-patch32` | Object detection / device localization | HuggingFace |
| `microsoft/Florence-2-large` | Detailed visual grounding and captioning | HuggingFace |
| `Qwen/Qwen2-VL-7B-Instruct` | Lightweight local VLM option | HuggingFace |

**Extraction Targets**:
- Device category (printer, microwave, router, etc.)
- Brand logo / model number (OCR on device label)
- Error indicators: LED color/pattern, display code, physical damage type
- Component visibility: port, panel, hose, fuse location

**Implementation**:
```python
# tools/vision_analyzer.py
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
import base64

class VisionAnalyzer:
    def analyze_image(self, image_path: str, user_description: str = "") -> DiagnosticPayload:
        # 1. Run object detection for device localization
        # 2. Run VLM for detailed analysis
        # 3. Run OCR for model number extraction
        # 4. Return structured DiagnosticPayload
        pass
```

**Output: `DiagnosticPayload`**
```json
{
  "device_category": "printer",
  "brand": "HP",
  "model_candidates": ["HP LaserJet Pro MFP M428fdw", "HP LaserJet Pro M404dn"],
  "model_confidence": 0.87,
  "error_indicators": {
    "led_pattern": "blinking_red_4x",
    "display_code": null,
    "physical_damage": []
  },
  "visible_components": ["paper_tray", "front_panel", "status_light"],
  "user_description": "Red light blinking 4 times repeatedly"
}
```

---

### 3.2 Device Identification & Fault Classification

**Purpose**: Map DiagnosticPayload → specific device model + fault type

**Approach**:
- **Device catalog embeddings**: Pre-embed device model descriptions, common error patterns
- **Semantic search**: Match DiagnosticPayload against catalog
- **ML Classification** (optional, Phase 2):
  - Fine-tuned classifier on device error pattern dataset
  - Model: `distilbert-base-uncased` fine-tuned on appliance error corpus
  - Dataset: Scraped from manufacturer support forums + manual error tables

**Fault Taxonomy**:
```
fault_type:
  - paper_jam
  - connectivity_error
  - hardware_failure
  - firmware_error
  - power_supply_issue
  - filter_clog
  - seal_failure
  - mechanical_wear
  - user_error
  - unknown
```

---

### 3.3 RAG Engine

**Purpose**: Retrieve precise repair procedures from the knowledge corpus

**Vector Database**: ChromaDB (Phase 1, local) → Qdrant (Phase 2, scalable)

**Corpus Sources**:
| Source | Content | Format | Update Frequency |
|---|---|---|---|
| Manufacturer websites | Official service manuals | PDF | Monthly |
| iFixit.com | Community repair guides | HTML/JSON | Weekly |
| ManualsLib.com | Device manuals (open) | PDF | Monthly |
| RepairClinic.com | Parts + symptoms database | HTML | Weekly |
| Research papers | Diagnostic ML techniques | PDF | Weekly auto-crawl |

**Embedding Model**: `BAAI/bge-large-en-v1.5` (HuggingFace, state-of-art retrieval)

**Retrieval Strategy**:
- Hybrid search: dense (semantic) + sparse (BM25 keyword)
- Re-ranking: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Top-k: 5 chunks, min relevance score: 0.72

**Chunking Strategy**:
- Repair procedures: chunk by step (one chunk per numbered instruction)
- Manuals: chunk by section with 50-token overlap
- Preserve: images references, part numbers, model applicability tags

---

### 3.4 Knowledge Self-Improvement Pipeline

**This is the core differentiator of the system.**

```
Weekly Automated Pipeline:
┌─────────────────────────────────────────┐
│  1. CRAWL (every Sunday 2:00 AM UTC)    │
│     - arXiv: cs.CV, cs.LG, eess.SP     │
│       (appliance diagnosis papers)      │
│     - iFixit API: new guides added      │
│     - Manufacturer bulletin RSS feeds   │
│     - RepairClinic symptom updates      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. FILTER & QUALITY CHECK              │
│     - Relevance score > 0.7             │
│     - Deduplicate vs existing corpus    │
│     - Flag conflicting information      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. EXTRACT & SUMMARIZE                 │
│     - LLM extracts key findings         │
│     - Structured into knowledge atoms   │
│     - Tagged: device_category, fault,   │
│       source, confidence, date          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. UPDATE KNOWLEDGE BRAIN              │
│     - Append to SECOND-KNOWLEDGE-       │
│       BRAIN.md (human-readable)         │
│     - Re-embed into vector DB           │
│     - Update BM25 index                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  5. VALIDATE                            │
│     - Run regression on test cases      │
│     - Alert if accuracy drops > 2%      │
└─────────────────────────────────────────┘
```

**Crawl Targets**:
```yaml
crawl_sources:
  arxiv:
    queries:
      - "appliance fault diagnosis deep learning"
      - "visual error detection home electronics"
      - "multimodal device troubleshooting"
    max_papers_per_run: 20
    
  iFixit:
    api_endpoint: "https://www.ifixit.com/api/2.0/guides"
    filters: ["category=Electronics", "difficulty<=moderate"]
    
  manufacturer_rss:
    - name: HP
      url: "https://support.hp.com/rss"
    - name: Canon
      url: "https://www.usa.canon.com/rss"
    # Extend as needed
```

---

### 3.5 Repair Guide Generator

**Purpose**: Synthesize retrieved knowledge into user-facing repair instructions

**Components**:
1. **Step Sequencer**: Orders repair steps logically from retrieved chunks
2. **Safety Assessor**: Classifies tier (1–4) and inserts appropriate warnings
3. **Image Linker**: Matches steps to relevant images from manufacturer catalogs
4. **Plain Language Translator**: Converts technical jargon to accessible language (LLM)
5. **Parts Finder**: Suggests where to buy needed parts (Amazon, RepairClinic links)

---

### 3.6 External LLM Router

**Purpose**: Allow users to plug in their preferred LLM API for enhanced reasoning

```python
# config/llm_router.py
class LLMRouter:
    PROVIDERS = {
        "claude": {
            "endpoint": "https://api.anthropic.com/v1/messages",
            "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
            "default": "claude-sonnet-4-6"
        },
        "openai": {
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "models": ["gpt-4o", "gpt-4o-mini"],
            "default": "gpt-4o"
        },
        "gemini": {
            "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
            "default": "gemini-2.0-flash"
        },
        "local": {
            "endpoint": "http://localhost:11434/api/chat",  # Ollama
            "models": ["llava", "mistral"],
            "default": "llava"
        }
    }
```

**User Configuration** (`.env` or `config.yaml`):
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4-6
LLM_API_KEY=sk-ant-...
VISION_PROVIDER=claude   # or openai, gemini
VISION_MODEL=claude-opus-4-6
```

---

## 4. ML/DL Components

### 4.1 Device Fingerprinting (Phase 2)
- **Task**: Multi-label classification of device type, brand, model from image
- **Approach**: Fine-tune `EfficientNet-B4` or `ConvNeXt-Tiny` on curated device image dataset
- **Dataset**: Scraped from Amazon product images + manufacturer websites (~50K images)
- **HuggingFace Hub**: Publish as `fixeragent/device-classifier-v1`

### 4.2 Error Code OCR
- **Task**: Extract alphanumeric error codes from device displays / labels
- **Model**: `microsoft/trocr-base-printed` (HuggingFace) — optimized for printed text
- **Augmentation**: Fine-tune on appliance display fonts (7-segment, LCD, LED)

### 4.3 LED Pattern Recognition
- **Task**: Classify blink patterns from video (e.g., "4 red blinks = paper jam")
- **Approach**: Simple CNN + temporal model (lightweight LSTM) on video frames
- **No full model training needed**: Rule-based pattern matching is sufficient for Phase 1
  (blink count via frame differencing → lookup table from manuals)

### 4.4 Repair Outcome Prediction (Phase 3)
- **Task**: Given device + fault + user skill level → predict repair success probability
- **Model**: Gradient Boosting (XGBoost) on historical repair outcome logs
- **Features**: device_age, fault_type, tier, user_feedback_history

---

## 5. Data Architecture

```
data/
├── manuals/               # Raw PDF manuals (by brand/model)
│   ├── HP/
│   ├── Canon/
│   ├── Samsung/
│   └── ...
├── corpus/                # Chunked, embedded documents
│   ├── embeddings/        # ChromaDB / Qdrant collections
│   └── bm25_index/        # Sparse retrieval index
├── knowledge_brain/
│   └── SECOND-KNOWLEDGE-BRAIN.md
├── device_catalog/
│   └── devices.json       # Device metadata, model numbers, specs
├── feedback_logs/
│   └── outcomes.jsonl     # User repair outcome logs
└── crawl_cache/
    └── last_run.json      # Crawl state tracking
```

---

## 6. API Endpoints (Phase 2+)

```
POST /diagnose
  Input: { image_base64, description?, device_hint? }
  Output: DiagnosticPayload + RepairGuide

POST /feedback
  Input: { session_id, outcome: "fixed"|"partial"|"failed", notes? }
  Output: { acknowledged: true }

GET /guide/{session_id}
  Output: Cached RepairGuide as JSON or HTML

POST /knowledge/crawl
  Auth: admin
  Output: { new_documents_added: int, errors: [] }

GET /health
  Output: { status, model_versions, kb_last_updated }
```

---

## 7. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.11+ | Ecosystem for AI/ML |
| Agent Framework | LangChain + LangGraph | Robust agentic loops |
| Vector DB | ChromaDB → Qdrant | Local-first, scalable |
| Embeddings | BAAI/bge-large-en-v1.5 | SOTA retrieval quality |
| Vision | Multi-provider (user config) | Flexibility |
| OCR | TrOCR (HuggingFace) | Best for printed/display text |
| Web Scraping | Scrapy + Playwright | JS-heavy sites |
| PDF Processing | PyMuPDF + pdfplumber | Manual extraction |
| API Layer | FastAPI | Performance + docs |
| Frontend (Phase 2) | Next.js + Tailwind | Modern UX |
| Scheduling | APScheduler / Celery | Knowledge update jobs |
| Monitoring | Loguru + Prometheus | Observability |
| Containerization | Docker + Docker Compose | Deployment |

---

## 8. Improvement Areas vs Original Concept

| Original | Enhancement | Rationale |
|---|---|---|
| Generic vision API | Multi-provider vision with fallback chain | Resilience + cost optimization |
| RAG from manufacturer docs | Hybrid dense+sparse retrieval + reranking | 30–40% better retrieval precision |
| Basic step guide | Safety tier system + escalation logic | Liability + user trust |
| Static knowledge | Auto-crawl + SECOND-KNOWLEDGE-BRAIN | Core differentiator: self-improvement |
| Single model | External LLM router (Claude/GPT/Gemini) | User flexibility, future-proof |
| Not specified | LED pattern recognition via video | Handles most common error signals |
| Not specified | Repair outcome feedback loop | Continuous accuracy improvement |
| Not specified | Parts sourcing links | Full end-to-end user journey |

---

## 9. Constraints & Risks

| Risk | Mitigation |
|---|---|
| Incorrect repair advice → injury | Mandatory safety tier system, legal disclaimer |
| Wrong device identification | Confidence threshold + user confirmation flow |
| Manual copyright issues | Only index publicly available / open manuals; respect robots.txt |
| Vision API cost | Cache results per image hash; support local VLM option |
| Knowledge staleness | Weekly automated crawl + staleness alerts |
| LLM hallucination in repair steps | Always ground in retrieved manual text; flag "estimated" steps |

---

*Document version: 0.1.0 | Created: Project initialization*
