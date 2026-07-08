"""Embedder abstraction (DIP)."""
from __future__ import annotations

import abc

from src.schemas.models import NewsChunk


class Embedder(abc.ABC):
    @abc.abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_chunk(self, chunk: NewsChunk) -> list[float]:
        return self.embed_batch([chunk.chunk_text])[0]
