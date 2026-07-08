"""OpenAI embedder (paid)."""
from __future__ import annotations

import os

from openai import OpenAI

from src.processors.embeddings.base import Embedder


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self._model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]
