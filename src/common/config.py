"""Configuration with singleton pattern (DIP)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Kafka
    kafka_bootstrap_servers: str = "localhost:29092"
    kafka_client_id: str = "news-rag"
    kafka_news_topic: str = "news.raw"
    kafka_processed_topic: str = "news.embedded"
    kafka_dlq_topic: str = "news.dlq"
    kafka_consumer_group: str = "flink-rag-pipeline"

    # Schema registry
    schema_registry_url: str = "http://localhost:8081"

    # Flink
    flink_jobmanager_rpc_address: str = "localhost"
    flink_rest_port: int = 8082

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "news_embeddings"
    qdrant_vector_size: int = 768

    # Embeddings
    embedding_provider: Literal["sentence_transformers", "openai"] = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    openai_api_key: str = ""

    # LLM
    llm_provider: Literal["openai", "anthropic", "stub", "llamacpp"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    # OpenAI-compatible base URL. Used by openai and llamacpp providers.
    # For llama.cpp: http://llama-server:8080/v1
    # Empty = fall back to OpenAI default (https://api.openai.com/v1).
    llm_base_url: str = ""

    # Scraping
    scraper_user_agent: str = "NewsRAGBot/1.0"
    scraper_rate_limit_rps: int = 2
    scraper_http_timeout: int = 30

    # Misc
    log_level: str = "INFO"
    project_root: Path = Field(default_factory=Path.cwd)

    @property
    def config_dir(self) -> Path:
        return self.project_root / "configs"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for global settings."""
    return Settings()
