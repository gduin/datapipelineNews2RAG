"""Qdrant implementation of VectorSink (ISP: implements only what we need)."""
from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from qdrant_client.http.exceptions import UnexpectedResponse

from src.common.config import get_settings
from src.common.exceptions import VectorStoreError
from src.common.logging import get_logger
from src.processors.sinks.base import VectorSink, VectorRecord

log = logging.getLogger(__name__)


class QdrantSink(VectorSink):
    def __init__(self, url: str | None = None, collection: str | None = None) -> None:
        s = get_settings()
        self._client = QdrantClient(url=url or s.qdrant_url)
        self._collection = collection or s.qdrant_collection
        self._logger = get_logger(__name__)

    def ensure_collection(self, vector_size: int) -> None:
        try:
            cols = {c.name for c in self._client.get_collections().collections}
        except UnexpectedResponse as exc:
            raise VectorStoreError(
                f"failed to list Qdrant collections at {self._client.url}: {exc}"
            ) from exc

        if self._collection not in cols:
            self._logger.info(
                "qdrant_collection_missing",
                collection=self._collection,
                vector_size=vector_size,
            )
            try:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
                )
            except UnexpectedResponse as exc:
                raise VectorStoreError(
                    f"failed to create Qdrant collection '{self._collection}': {exc}"
                ) from exc
        else:
            self._logger.debug(
                "qdrant_collection_exists", collection=self._collection
            )

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        try:
            self._client.upsert(
                collection_name=self._collection,
                points=[
                    qm.PointStruct(id=r.id, vector=r.vector, payload=r.payload)
                    for r in records
                ],
                wait=True,
            )
        except UnexpectedResponse as exc:
            raise VectorStoreError(
                f"qdrant upsert failed for {len(records)} points: {exc}"
            ) from exc
        return len(records)
