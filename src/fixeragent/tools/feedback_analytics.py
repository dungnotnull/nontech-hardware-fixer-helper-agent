"""Feedback analytics pipeline — parse outcomes, identify weak areas, generate reports."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from fixeragent.config import get_settings


class FeedbackAnalytics:
    """Analyze repair outcome logs to find gaps and improve retrieval."""

    def __init__(self, log_path: str | Path | None = None) -> None:
        self.settings = get_settings()
        self.log_path = Path(log_path or self.settings.feedback_log_path)

    def load_outcomes(self, days: int | None = None) -> list[dict[str, Any]]:
        """Load feedback entries from JSONL file."""
        if not self.log_path.exists():
            return []
        outcomes: list[dict[str, Any]] = []
        cutoff = datetime.utcnow() - timedelta(days=days) if days else None
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if cutoff:
                            ts = datetime.fromisoformat(entry.get("timestamp", "1970-01-01"))
                            if ts < cutoff:
                                continue
                        outcomes.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to load outcomes: {e}")
        return outcomes

    def summary(self, days: int = 30) -> dict[str, Any]:
        """High-level metrics."""
        outcomes = self.load_outcomes(days=days)
        total = len(outcomes)
        if total == 0:
            return {"period_days": days, "total": 0}
        fixed = sum(1 for o in outcomes if o.get("outcome") == "fixed")
        partial = sum(1 for o in outcomes if o.get("outcome") == "partial")
        failed = sum(1 for o in outcomes if o.get("outcome") == "failed")
        return {
            "period_days": days,
            "total": total,
            "fixed": fixed,
            "partial": partial,
            "failed": failed,
            "success_rate": round((fixed + partial * 0.5) / total, 4),
        }

    def weak_categories(self, threshold: float = 0.60, days: int = 90) -> list[dict[str, Any]]:
        """Identify fault categories with success rate below threshold."""
        outcomes = self.load_outcomes(days=days)
        by_category: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "fixed": 0, "partial": 0, "failed": 0})
        for o in outcomes:
            cat = o.get("fault_type", "unknown")
            by_category[cat]["total"] += 1
            by_category[cat][o.get("outcome", "failed")] += 1

        weak: list[dict[str, Any]] = []
        for cat, counts in by_category.items():
            if counts["total"] < 5:
                continue
            success = (counts["fixed"] + counts["partial"] * 0.5) / counts["total"]
            if success < threshold:
                weak.append({
                    "category": cat,
                    "total_attempts": counts["total"],
                    "success_rate": round(success, 4),
                    "fixed": counts["fixed"],
                    "partial": counts["partial"],
                    "failed": counts["failed"],
                })
        weak.sort(key=lambda x: x["success_rate"])
        return weak

    def monthly_report(self, year: int, month: int) -> dict[str, Any]:
        """Generate a structured monthly performance report."""
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        outcomes = [
            o for o in self.load_outcomes()
            if start <= datetime.fromisoformat(o.get("timestamp", "1970-01-01")) < end
        ]
        summary = self._compute_summary(outcomes)
        return {
            "year": year,
            "month": month,
            **summary,
            "weak_categories": self._weak_from_outcomes(outcomes),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _compute_summary(self, outcomes: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(outcomes)
        if total == 0:
            return {"total": 0}
        fixed = sum(1 for o in outcomes if o.get("outcome") == "fixed")
        partial = sum(1 for o in outcomes if o.get("outcome") == "partial")
        failed = sum(1 for o in outcomes if o.get("outcome") == "failed")
        return {
            "total": total,
            "fixed": fixed,
            "partial": partial,
            "failed": failed,
            "success_rate": round((fixed + partial * 0.5) / total, 4),
        }

    def _weak_from_outcomes(self, outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_cat: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "fixed": 0, "partial": 0, "failed": 0})
        for o in outcomes:
            cat = o.get("fault_type", "unknown")
            by_cat[cat]["total"] += 1
            by_cat[cat][o.get("outcome", "failed")] += 1
        weak = []
        for cat, c in by_cat.items():
            if c["total"] < 3:
                continue
            sr = (c["fixed"] + c["partial"] * 0.5) / c["total"]
            if sr < 0.60:
                weak.append({"category": cat, "success_rate": round(sr, 4), "attempts": c["total"]})
        weak.sort(key=lambda x: x["success_rate"])
        return weak