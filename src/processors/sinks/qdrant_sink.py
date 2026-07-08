"""Qdrant implementation of VectorSink (ISP: implements only what we need)."""
from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from src.common.config import get_settings
from src.processors.sinks.base import VectorSink, VectorRecord


class QdrantSink(VectorSink):
    def __init__(self, url: str | None = None, collection: str | None = None) -> None:
        s = get_settings()
        self._client = QdrantClient(url=url or s.qdrant_url)
        self._collection = collection or s.qdrant_collection

    def ensure_collection(self, vector_size: int) -> None:
        cols = {c.name for c in self._client.get_collections().collections}
        if self._collection not in cols:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
            )

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        self._client.upsert(
            collection_name=self._collection,
            points=[
                qm.PointStruct(id=r.id, vector=r.vector, payload=r.payload)
                for r in records
            ],
            wait=True,
        )
        return len(records)
