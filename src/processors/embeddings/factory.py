"""Embedder factory."""
from __future__ import annotations

import logging

from src.common.config import get_settings
from src.common.exceptions import EmbeddingError
from src.processors.embeddings.base import Embedder
from src.processors.embeddings.openai_embedder import OpenAIEmbedder
from src.processors.embeddings.sentence_transformers_embedder import SentenceTransformersEmbedder

log = logging.getLogger(__name__)


def build_embedder() -> Embedder:
    settings = get_settings()
    provider = settings.embedding_provider
    log.info(
        "building_embedder",
        provider=provider,
        model=settings.embedding_model,
    )
    try:
        match provider:
            case "sentence_transformers":
                return SentenceTransformersEmbedder()
            case "openai":
                return OpenAIEmbedder()
            case _:
                raise EmbeddingError(f"unknown embedding provider: {provider}")
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError(
            f"failed to instantiate embedder for provider '{provider}': {exc}"
        ) from exc
