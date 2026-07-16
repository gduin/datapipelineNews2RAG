"""OpenAI embedder (paid)."""
from __future__ import annotations

import os

from openai import OpenAI, APIConnectionError, APITimeoutError
from openai._exceptions import RateLimitError

from src.common.exceptions import EmbeddingError
from src.processors.embeddings.base import Embedder


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str = "text-embedding-3-small") -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EmbeddingError("OPENAI_API_KEY environment variable is not set")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = self._client.embeddings.create(model=self._model, input=texts)
        except RateLimitError as exc:
            raise EmbeddingError(f"OpenAI rate limit exceeded: {exc}") from exc
        except APITimeoutError as exc:
            raise EmbeddingError(f"OpenAI request timed out: {exc}") from exc
        except APIConnectionError as exc:
            raise EmbeddingError(f"OpenAI connection error: {exc}") from exc
        except Exception as exc:
            raise EmbeddingError(f"unexpected OpenAI error: {exc}") from exc

        if len(resp.data) != len(texts):
            raise EmbeddingError(
                f"OpenAI returned {len(resp.data)} results for {len(texts)} inputs"
            )
        return [d.embedding for d in resp.data]
