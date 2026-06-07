"""Prometheus instrumentation for API and agent metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Info, Gauge, start_http_server
from loguru import logger

APP_INFO = Info("fixeragent", "Application information")
DIAGNOSE_REQUESTS = Counter("diagnose_requests_total", "Total diagnosis requests", ["status"])
DIAGNOSE_LATENCY = Histogram("diagnose_latency_seconds", "Diagnosis latency")
FEEDBACK_COUNTER = Counter("feedback_total", "Total feedback submissions", ["outcome"])
KB_SIZE_GAUGE = Gauge("knowledge_base_documents", "Number of documents in KB")
REPAIR_TIER_COUNTER = Counter("repair_tier_total", "Repairs by tier", ["tier"])


def start_metrics_server(port: int = 9090) -> None:
    APP_INFO.info({"version": "0.1.0"})
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.warning(f"Metrics server failed to start: {e}")