"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "claude"
    llm_model: str = "claude-sonnet-4-6"
    llm_api_key: str | None = None
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2000

    # Vision
    vision_provider: str = "claude"
    vision_model: str = "claude-opus-4-6"
    vision_api_key: str | None = None

    # Local / Ollama
    local_llm_endpoint: str = "http://localhost:11434/api/chat"
    local_vision_endpoint: str = "http://localhost:11434/api/chat"

    # Vector DB
    chroma_persist_dir: str = "./data/corpus/embeddings"
    chroma_collection_name: str = "fixeragent_manuals"
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Logging
    log_level: str = "INFO"
    log_file: str = "./data/logs/fixeragent.log"

    # Agent thresholds
    diagnostic_confidence_threshold: float = 0.80
    device_id_confidence_threshold: float = 0.85
    safety_escalation_enabled: bool = True

    # Paths
    knowledge_brain_path: str = "./data/knowledge_brain/SECOND-KNOWLEDGE-BRAIN.md"
    device_catalog_path: str = "./data/device_catalog/devices.json"
    feedback_log_path: str = "./data/feedback_logs/outcomes.jsonl"
    manuals_dir: str = "./data/manuals"


@lru_cache
def get_settings() -> Settings:
    return Settings()
