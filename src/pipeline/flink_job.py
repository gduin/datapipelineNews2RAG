"""Main PyFlink job: Kafka -> transform -> embed -> Qdrant + Kafka."""
from __future__ import annotations

import json

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction
from pyflink.common import Types

from src.common.config import get_settings
from src.common.logging import configure_logging, get_logger
from src.pipeline.builder import PipelineBuilder, PipelineConfig
from src.processors.transformations.cleaning import NormalizeStep
from src.processors.transformations.chunking import SentenceChunker
from src.processors.embeddings.factory import build_embedder
from src.processors.sinks.qdrant_sink import QdrantSink
from src.processors.sinks.base import VectorRecord
from src.schemas.models import NewsItem


class ProcessFunction(MapFunction):
    """Stateless MapFunction that cleans, chunks, embeds and writes to Qdrant."""

    def __init__(self) -> None:
        self._normalize = NormalizeStep()
        self._chunker = SentenceChunker(max_tokens=512, overlap_tokens=64)
        self._embedder = None
        self._sink = None

    def open(self, runtime_context):  # noqa: ANN001
        self._embedder = build_embedder()
        self._sink = QdrantSink()
        self._sink.ensure_collection(get_settings().qdrant_vector_size)

    def map(self, value):  # noqa: ANN001
        logger = get_logger(__name__)
        try:
            item_dict = json.loads(value) if isinstance(value, str) else value
        except Exception as exc:  # noqa: BLE001
            logger.error("decode_failed", error=str(exc))
            return None

        ni = NewsItem(**item_dict)
        normalized = self._normalize.process(ni)
        if not normalized:
            return None
        chunks = self._chunker.process(normalized)
        if not chunks:
            return None

        embeddings = self._embedder.embed_batch([c.chunk_text for c in chunks])
        records = [
            VectorRecord(
                id=c.chunk_id,
                vector=emb,
                payload={
                    "url": c.url, "title": c.title, "chunk_text": c.chunk_text,
                    "chunk_index": c.chunk_index, "total_chunks": c.total_chunks,
                    "language": c.language, "published_at": c.published_at,
                    "source_id": c.source_id, "tags": c.tags,
                },
            )
            for c, emb in zip(chunks, embeddings)
        ]
        self._sink.upsert(records)
        logger.info("ingested", url=ni.url, chunks=len(records))
        return json.dumps({"url": ni.url, "chunks": len(records)})


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    env = StreamExecutionEnvironment.get_execution_environment()
    config = PipelineConfig(
        source_topic=settings.kafka_news_topic,
        sink_topic=settings.kafka_processed_topic,
        group_id=settings.kafka_consumer_group,
        bootstrap=settings.kafka_bootstrap_servers,
        parallelism=4,
    )
    builder = PipelineBuilder(env, config)
    stream = builder.build()
    stream.map(ProcessFunction(), output_type=Types.STRING()).name("embed-and-sink")
    env.execute("news-rag-pipeline")


if __name__ == "__main__":
    main()
