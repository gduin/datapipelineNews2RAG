"""Local Sentence Transformers embedder."""
from __future__ import annotations

from functools import lru_cache

from src.common.config import get_settings
from src.common.exceptions import EmbeddingError
from src.processors.embeddings.base import Embedder


@lru_cache(maxsize=1)
def _load_model(name: str):
    from sentence_transformers import SentenceTransformer  # type: ignore
    return SentenceTransformer(name)


class SentenceTransformersEmbedder(Embedder):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().embedding_model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            model = _load_model(self._model_name)
        except Exception as exc:
            raise EmbeddingError(
                f"failed to load model '{self._model_name}': {exc}"
            ) from exc

        try:
            embeddings = model.encode(texts, show_progress_bar=False)
        except Exception as exc:
            raise EmbeddingError(
                f"model.encode failed for {len(texts)} texts: {exc}"
            ) from exc

        if len(embeddings) != len(texts):
            raise EmbeddingError(
                f"model returned {len(embeddings)} embeddings for {len(texts)} inputs"
            )
        return [list(map(float, vec)) for vec in embeddings]
