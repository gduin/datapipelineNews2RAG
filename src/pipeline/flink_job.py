"""Main PyFlink job: Kafka -> transform -> embed -> Qdrant + Kafka."""
from __future__ import annotations

import json
import traceback

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction
from pyflink.common import Types

from src.common.config import get_settings
from src.common.exceptions import EmbeddingError, VectorStoreError, SchemaError
from src.common.logging import configure_logging, get_logger
from src.pipeline.builder import PipelineBuilder, PipelineConfig
from src.processors.embeddings.factory import build_embedder
from src.processors.sinks.qdrant_sink import QdrantSink
from src.processors.sinks.base import VectorRecord
from src.processors.transformations.chunking import SentenceChunker
from src.processors.transformations.cleaning import NormalizeStep
from src.schemas.models import NewsItem


class ProcessFunction(MapFunction):
    """MapFunction that cleans, chunks, embeds and writes to Qdrant."""

    def __init__(self) -> None:
        self._normalize = None
        self._chunker = None
        self._embedder = None
        self._sink = None
        self._logger = None

    def open(self, runtime_context):  # noqa: ANN001
        configure_logging(get_settings().log_level)
        self._logger = get_logger(__name__)
        self._logger.info("process_function_opening")
        try:
            self._normalize = NormalizeStep()
            self._chunker = SentenceChunker()
            self._embedder = build_embedder()
            self._sink = QdrantSink()
            self._sink.ensure_collection(get_settings().qdrant_vector_size)
            self._logger.info(
                "process_function_ready",
                qdrant_collection=get_settings().qdrant_collection,
                vector_size=get_settings().qdrant_vector_size,
                embedding_provider=get_settings().embedding_provider,
            )
        except Exception:
            self._logger.critical("process_function_open_failed", exc_info=True)
            raise

    def map(self, value):  # noqa: ANN001
        logger = get_logger(__name__)
        try:
            item_dict = _decode_value(value)
            ni = NewsItem(**item_dict)
        except SchemaError as exc:
            logger.warning("schema_invalid", error=str(exc))
            return None
        except Exception as exc:
            logger.error("decode_failed", error=str(exc), value_sample=_safe_str(value, 200))
            return None

        normalized = self._normalize.process(ni) if self._normalize else None
        if not normalized:
            logger.debug("normalized_dropped", url=ni.url)
            return None

        chunks = self._chunker.process(normalized) if self._chunker else None
        if not chunks:
            logger.debug("chunked_dropped", url=ni.url)
            return None

        try:
            embeddings = self._embedder.embed_batch([c.chunk_text for c in chunks])
        except Exception as exc:
            logger.error(
                "embedding_failed",
                url=ni.url,
                chunks_count=len(chunks),
                error=str(exc),
                exc_info=True,
            )
            return None

        try:
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
        except (VectorStoreError, Exception) as exc:
            logger.error(
                "sink_upsert_failed",
                url=ni.url,
                chunks_count=len(records) if records else 0,
                error=str(exc),
                exc_info=True,
            )
            return None

        logger.info("ingested", url=ni.url, chunks=len(records))
        return json.dumps({"url": ni.url, "chunks": len(records)})


def _decode_value(value) -> dict:
    """Decode the Kafka source output into a dict.

    JsonRowDeserializationSchema with Types.ROW emits a pyflink Row;
    raw JSON strings come through unchanged.
    """
    if value is None:
        raise SchemaError("received None from Kafka source")

    if hasattr(value, "getField"):
        raw = value.getField(0)
    elif isinstance(value, (list, tuple)):
        raw = value[0]
    elif isinstance(value, dict):
        raw = value
    elif isinstance(value, str):
        raw = value
    else:
        raise SchemaError(
            f"unexpected Kafka value type: {type(value).__name__}"
        )

    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"invalid JSON in Kafka value: {exc}") from exc

    if isinstance(raw, dict):
        return raw

    raise SchemaError(f"cannot extract dict from Kafka value: {type(raw).__name__}")


def _safe_str(value, max_len: int = 200) -> str:
    try:
        text = str(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    logger.info(
        "starting_pipeline",
        kafka_topic=settings.kafka_news_topic,
        kafka_bootstrap=settings.kafka_bootstrap_servers,
        qdrant_collection=settings.qdrant_collection,
        embedding_provider=settings.embedding_provider,
    )
    try:
        env = StreamExecutionEnvironment.get_execution_environment()
        config = PipelineConfig(
            source_topic=settings.kafka_news_topic,
            sink_topic=settings.kafka_processed_topic,
            group_id=settings.kafka_consumer_group,
            bootstrap=settings.kafka_bootstrap_servers,
            parallelism=2,
        )
        builder = PipelineBuilder(env, config)
        stream = builder.build()
        stream.map(ProcessFunction(), output_type=Types.STRING()).name("embed-and-sink")
        logger.info("execution_environment_configured", parallelism=2)
        env.execute("news-rag-pipeline")
    except Exception:
        logger.critical("pipeline_execution_failed", exc_info=True)
        raise


if __name__ == "__main__":
    main()
