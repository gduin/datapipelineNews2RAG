"""Orchestrator ties transformations and embedders locally (non-Flink tests)."""
from __future__ import annotations

import logging

from dataclasses import dataclass

from src.common.exceptions import EmbeddingError, VectorStoreError
from src.common.logging import get_logger
from src.processors.base import NewsItemStep, ChunkStep
from src.processors.embeddings.base import Embedder
from src.processors.sinks.base import VectorSink, VectorRecord
from src.processors.transformations.cleaning import NormalizeStep
from src.processors.transformations.chunking import SentenceChunker
from src.schemas.models import NewsItem

log = logging.getLogger(__name__)


@dataclass
class Pipeline:
    normalize: NewsItemStep
    chunker: ChunkStep
    embedder: Embedder
    sink: VectorSink

    def process(self, item: NewsItem) -> int:
        logger = get_logger(__name__)
        logger.debug("processing_item", url=item.url)
        try:
            norm = self.normalize.process(item)
            if not norm:
                logger.debug("normalized_dropped", url=item.url)
                return 0
            chunks = self.chunker.process(norm) or []
            if not chunks:
                logger.debug("chunked_dropped", url=item.url)
                return 0

            vectors = self.embedder.embed_batch([c.chunk_text for c in chunks])
            records = [
                VectorRecord(
                    id=c.chunk_id, vector=v,
                    payload={"url": c.url, "title": c.title, "chunk_text": c.chunk_text,
                             "chunk_index": c.chunk_index, "total_chunks": c.total_chunks,
                             "language": c.language, "published_at": c.published_at,
                             "source_id": c.source_id, "tags": c.tags},
                ) for c, v in zip(chunks, vectors)
            ]
            inserted = self.sink.upsert(records)
            logger.info(
                "item_processed",
                url=item.url,
                chunks=len(chunks),
                inserted=inserted,
            )
            return inserted
        except (EmbeddingError, VectorStoreError):
            raise
        except Exception as exc:
            logger.error("process_failed", url=item.url, error=str(exc), exc_info=True)
            return 0


def default_pipeline(embedder: Embedder, sink: VectorSink) -> Pipeline:
    return Pipeline(
        normalize=NormalizeStep(),
        chunker=SentenceChunker(),
        embedder=embedder,
        sink=sink,
    )
