"""Local Sentence Transformers embedder."""
from __future__ import annotations

from functools import lru_cache

from src.common.config import get_settings
from src.processors.embeddings.base import Embedder


@lru_cache(maxsize=1)
def _load_model(name: str):
    from sentence_transformers import SentenceTransformer  # type: ignore
    return SentenceTransformer(name)


class SentenceTransformersEmbedder(Embedder):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().embedding_model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = _load_model(self._model_name)
        return [list(map(float, vec)) for vec in model.encode(texts, show_progress_bar=False)]
