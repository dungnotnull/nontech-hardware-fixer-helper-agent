"""FastAPI application — production-ready backend."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from fixeragent.agents import FixerAgent
from fixeragent.api.auth import APIKeyAuth, require_admin
from fixeragent.api.rate_limit import RateLimiter
from fixeragent.config import configure_logging, get_settings
from fixeragent.models import (
    DiagnosisRequest,
    DiagnosisResponse,
    FeedbackOutcome,
    LLMConfig,
    OutcomeStatus,
    RepairGuide,
)
from fixeragent.tools.rag_engine import RAGEngine
from fixeragent.tools.repairclinic_scraper import RepairClinicScraper
from fixeragent.tools.rss_scraper import RSSBulletinScraper
from fixeragent.tools.arxiv_crawler import ArxivCrawler
from fixeragent.tools.ifixit_client import iFixitClient

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    logger.warning("Redis async client not available")


# -----------------------------------------------------------------
# Lifespan
# -----------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("FixerAgent API starting up")
    settings = get_settings()
    # Pre-load knowledge brain on startup
    try:
        rag = RAGEngine()
        rag.load_knowledge_brain()
        app.state.rag = rag
        logger.info("Knowledge brain pre-loaded")
    except Exception as e:
        logger.warning(f"Knowledge brain preload failed: {e}")

    # Init Redis if available
    if REDIS_AVAILABLE and settings.redis_url:
        try:
            app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            await app.state.redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            app.state.redis = None
    else:
        app.state.redis = None

    yield

    # Shutdown
    if hasattr(app.state, "redis") and app.state.redis:
        await app.state.redis.close()
    logger.info("FixerAgent API shutting down")


# -----------------------------------------------------------------
# App instance
# -----------------------------------------------------------------

app = FastAPI(
    title="FixerAgent API",
    description="AI-powered home appliance repair assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_auth = APIKeyAuth()
rate_limiter = RateLimiter(redis_client=None, max_requests=30, window_seconds=60)

# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------

async def get_rate_limited(request: Request) -> None:
    rate_limiter.check(request)


# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/diagnose", response_model=DiagnosisResponse, dependencies=[Depends(get_rate_limited)])
async def diagnose(
    request: Request,
    image: UploadFile | None = None,
    description: str = "",
    device_hint: str = "",
    llm_provider: str = "claude",
    llm_model: str = "",
    llm_api_key: str = "",
) -> DiagnosisResponse:
    """Upload an image + description → receive a repair guide."""
    llm_config = LLMConfig(
        provider=llm_provider,
        model=llm_model or "claude-sonnet-4-6",
        api_key=llm_api_key or None,
    )
    agent = FixerAgent(llm_config=llm_config)

    image_path: str | None = None
    if image:
        ext = Path(image.filename).suffix or ".jpg"
        tmp_path = Path(f"/tmp/fixer_{uuid.uuid4().hex}{ext}")
        tmp_path.write_bytes(await image.read())
        image_path = str(tmp_path)

    try:
        result = agent.diagnose(
            image_path=image_path,
            description=description,
            device_hint=device_hint,
            llm_config=llm_config,
        )
    finally:
        if image_path:
            Path(image_path).unlink(missing_ok=True)

    return result


@app.post("/diagnose/json", response_model=DiagnosisResponse, dependencies=[Depends(get_rate_limited)])
async def diagnose_json(payload: DiagnosisRequest) -> DiagnosisResponse:
    """JSON-based diagnosis (image as base64 string)."""
    image_path: str | None = None
    if payload.image_base64:
        tmp_path = Path(f"/tmp/fixer_{uuid.uuid4().hex}.jpg")
        import base64
        tmp_path.write_bytes(base64.b64decode(payload.image_base64))
        image_path = str(tmp_path)

    agent = FixerAgent(llm_config=payload.llm_config)
    try:
        result = agent.diagnose(
            image_path=image_path,
            description=payload.description,
            device_hint=payload.device_hint,
            llm_config=payload.llm_config,
        )
    finally:
        if image_path:
            Path(image_path).unlink(missing_ok=True)
    return result


@app.post("/feedback")
async def feedback(payload: FeedbackOutcome) -> dict[str, Any]:
    """Submit feedback on a repair attempt."""
    agent = FixerAgent()
    return agent.feedback(
        session_id=payload.session_id,
        outcome=payload.outcome.value,
        notes=payload.notes,
    )


@app.get("/guide/{session_id}")
async def get_guide(session_id: str) -> dict[str, Any]:
    """Retrieve a cached repair guide by session ID."""
    # In production this reads from Redis or DB
    return {"session_id": session_id, "status": "not_implemented_in_memory_cache"}


@app.post("/knowledge/crawl", dependencies=[Depends(require_admin(api_key_auth))])
async def knowledge_crawl(request: Request, dry_run: bool = False) -> dict[str, Any]:
    """Admin: trigger knowledge crawl pipeline."""
    from fixeragent.scripts.knowledge_updater import KnowledgeUpdater
    updater = KnowledgeUpdater(rag=request.app.state.get("rag"))
    status = await updater.run(dry_run=dry_run)
    return status


@app.post("/knowledge/ingest", dependencies=[Depends(require_admin(api_key_auth))])
async def knowledge_ingest(
    request: Request,
    directory: str | None = None,
    pdf_files: list[UploadFile] | None = None,
) -> dict[str, Any]:
    """Admin: ingest PDF manuals into knowledge base."""
    rag: RAGEngine = request.app.state.get("rag") or RAGEngine()
    count = 0
    if directory:
        rag.ingest_directory(directory)
    if pdf_files:
        for pdf in pdf_files:
            ext = Path(pdf.filename).suffix or ".pdf"
            tmp = Path(f"/tmp/ingest_{uuid.uuid4().hex}{ext}")
            tmp.write_bytes(await pdf.read())
            try:
                rag.add_pdf(str(tmp), metadata={"uploaded": True, "filename": pdf.filename})
                count += 1
            finally:
                tmp.unlink(missing_ok=True)
    rag.persist()
    return {"ingested": count, "status": "ok"}


@app.get("/knowledge/status")
async def knowledge_status(request: Request) -> dict[str, Any]:
    """Get last crawl status and KB size."""
    rag: RAGEngine = request.app.state.get("rag") or RAGEngine()
    cache_path = Path(rag.persist_dir) / "crawl_status.json"
    status_data: dict[str, Any] = {}
    if cache_path.exists():
        status_data = json.loads(cache_path.read_text(encoding="utf-8"))
    return {
        "kb_documents": len(rag._corpus_texts),
        "chroma_ready": rag._collection is not None,
        "bm25_ready": rag._bm25 is not None,
        **status_data,
    }


@app.get("/devices")
async def list_devices() -> dict[str, Any]:
    """List supported device categories and brands."""
    catalog_path = Path(get_settings().device_catalog_path)
    if catalog_path.exists():
        return json.loads(catalog_path.read_text(encoding="utf-8"))
    return {"categories": [], "brands": {}}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "path": request.url.path},
    )