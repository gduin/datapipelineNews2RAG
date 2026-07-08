"""Embedder factory."""
from __future__ import annotations

from src.common.config import get_settings
from src.processors.embeddings.base import Embedder
from src.processors.embeddings.openai_embedder import OpenAIEmbedder
from src.processors.embeddings.sentence_transformers_embedder import SentenceTransformersEmbedder


def build_embedder() -> Embedder:
    settings = get_settings()
    match settings.embedding_provider:
        case "sentence_transformers":
            return SentenceTransformersEmbedder()
        case "openai":
            return OpenAIEmbedder()
        case _:
            raise ValueError(f"Unknown provider: {settings.embedding_provider}")
