"""Celery background tasks."""

from __future__ import annotations

from loguru import logger

from fixeragent.celery_config import celery_app

if celery_app:
    @celery_app.task(bind=True, max_retries=3)
    def async_diagnose(self, image_base64: str | None, description: str, device_hint: str, llm_config_dict: dict) -> dict:
        """Run diagnosis asynchronously for long-running vision jobs."""
        try:
            from fixeragent.agents import FixerAgent
            from fixeragent.models import LLMConfig
            llm_config = LLMConfig(**llm_config_dict)
            agent = FixerAgent(llm_config=llm_config)
            result = agent.diagnose(
                image_path=None,  # base64 handled separately in production
                description=description,
                device_hint=device_hint,
                llm_config=llm_config,
            )
            return result.model_dump()
        except Exception as exc:
            logger.exception("Async diagnosis failed")
            raise self.retry(exc=exc, countdown=60)

    @celery_app.task
    def weekly_knowledge_crawl() -> dict:
        """Scheduled weekly knowledge update."""
        import asyncio
        from fixeragent.scripts.knowledge_updater import KnowledgeUpdater
        updater = KnowledgeUpdater()
        return asyncio.run(updater.run())

    @celery_app.task
    def train_outcome_predictor() -> dict:
        """Retrain XGBoost model on latest feedback."""
        from fixeragent.tools.feedback_analytics import FeedbackAnalytics
        from fixeragent.tools.outcome_predictor import OutcomePredictor
        analytics = FeedbackAnalytics()
        outcomes = analytics.load_outcomes()
        predictor = OutcomePredictor()
        predictor.train(outcomes)
        return {"trained_on": len(outcomes)}