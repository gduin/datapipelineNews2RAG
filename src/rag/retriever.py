"""Vector retrieval with Qdrant (Repository pattern)."""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient

from src.common.config import get_settings
from src.processors.embeddings.base import Embedder


@dataclass(frozen=True)
class RetrievedDoc:
    url: str
    title: str | None
    chunk_text: str
    score: float


class NewsRetriever:
    def __init__(self, embedder: Embedder, client: QdrantClient | None = None) -> None:
        s = get_settings()
        self._embedder = embedder
        self._client = client or QdrantClient(url=s.qdrant_url)
        self._collection = s.qdrant_collection

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDoc]:
        vector = self._embedder.embed_batch([query])[0]
        results = self._client.search(
            collection_name=self._collection, query_vector=vector, limit=top_k
        )
        return [
            RetrievedDoc(
                url=p.payload.get("url", ""),
                title=p.payload.get("title"),
                chunk_text=p.payload.get("chunk_text", ""),
                score=p.score or 0.0,
            ) for p in results
        ]
