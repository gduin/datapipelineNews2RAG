import pytest
from datetime import datetime, timezone

from src.processors.transformations.deduplication import DeduplicateStep
from src.common.config import Settings, get_settings
from src.common.exceptions import (
    PipelineError, ScrapingError, ParsingError,
    EmbeddingError, VectorStoreError, SchemaError,
)
from src.common.logging import configure_logging, get_logger
from src.common.decorators import with_metrics, resilient, gather_with_concurrency
from src.schemas.models import NewsItem, NewsChunk
from src.processors.base import TransformationStep, NewsItemStep, ChunkStep
from src.processors.sinks.base import VectorSink, VectorRecord
from src.scrapers.base import SourceConfig, NewsSource, ParsingStrategy


# ── Config ───────────────────────────────────────────────────────────────────

class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.qdrant_collection == "news_embeddings"
        assert s.qdrant_vector_size == 768
        assert s.embedding_provider == "sentence_transformers"
        assert s.llm_provider in ("openai", "anthropic", "stub", "llamacpp")
        assert s.llm_temperature == 0.2

    def test_config_dir(self):
        s = Settings()
        assert s.config_dir.name == "configs"

    def test_singleton(self):
        a = get_settings()
        b = get_settings()
        assert a is b


# ── Exceptions ────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self):
        for cls in [ScrapingError, ParsingError, EmbeddingError, VectorStoreError, SchemaError]:
            assert issubclass(cls, PipelineError)

    def test_instantiate_all(self):
        for cls in [ScrapingError, ParsingError, EmbeddingError, VectorStoreError, SchemaError]:
            e = cls("msg")
            assert str(e) == "msg"
            assert isinstance(e, PipelineError)


# ── Logging ────────────────────────────────────────────────────────────────────

class TestLogging:
    def test_configure_logging(self):
        configure_logging()
        logger = get_logger("test")
        logger.info("hello")
        assert True

    def test_get_logger_with_name(self):
        logger = get_logger("my.module")
        assert logger is not None

    def test_get_logger_default(self):
        logger = get_logger()
        assert logger is not None


# ── Decorators ─────────────────────────────────────────────────────────────────

class TestDecorators:
    def test_with_metrics_sync(self):
        @with_metrics("test_metric")
        def heavy():
            return 42
        assert heavy() == 42

    def test_with_metrics_exception(self):
        @with_metrics("test_metric_fail")
        def raises():
            raise ValueError("boom")
        with pytest.raises(ValueError, match="boom"):
            raises()

    def test_resilient_success(self):
        @resilient(stop_after=3, max_wait=0.01)
        def test():
            return "ok"
        assert test() == "ok"

    def test_resilient_retries(self):
        calls = []
        @resilient(stop_after=3, max_wait=0.01)
        def test():
            calls.append(1)
            raise RuntimeError("transient")
        with pytest.raises(RuntimeError):
            test()
        assert len(calls) == 3


# ── Models ─────────────────────────────────────────────────────────────────────

class TestModels:
    def test_newsitem_minimal(self):
        ni = NewsItem(source_id="src", url="http://x")
        assert ni.source_id == "src"
        assert ni.url == "http://x"
        assert ni.title is None
        assert ni.tags == []

    def test_newsitem_full(self):
        ni = NewsItem(
            source_id="src", url="http://x",
            title="T", summary="S", content="C",
            author="A", published_at=1234567890,
            language="en", tags=["finance", "economy"],
            fetched_at=1234567900,
        )
        assert ni.title == "T"
        assert ni.published_at == 1234567890
        assert len(ni.tags) == 2

    def test_newsitem_immutable(self):
        ni = NewsItem(source_id="src", url="http://x", title="old")
        with pytest.raises(Exception):
            ni.title = "new"

    def test_newschunk(self):
        chunk = NewsChunk(
            chunk_id="abc", url="http://x",
            title="T", chunk_text="hello",
            chunk_index=0, total_chunks=1,
            language="en", published_at=1,
            source_id="src", tags=["news"],
        )
        assert chunk.chunk_id == "abc"
        assert chunk.chunk_text == "hello"


# ── Processor base ─────────────────────────────────────────────────────────────

class TestProcessorBase:
    def test_transformation_step_abstract(self):
        with pytest.raises(TypeError):
            TransformationStep()

    def test_newsitem_step_subclass(self):
        class Dummy(NewsItemStep):
            def process(self, item):
                return item
        step = Dummy()
        item = NewsItem(source_id="s", url="u")
        assert step.process(item) == item

    def test_chunk_step_subclass(self):
        class Dummy(ChunkStep):
            def process(self, item):
                return [NewsChunk("id", "u", "t", "c", 0, 1, "en", 1, "s", [])]
        step = Dummy()
        chunks = step.process(NewsItem(source_id="s", url="u"))
        assert len(chunks) == 1


# ── Sink base ──────────────────────────────────────────────────────────────────

class TestSinkBase:
    def test_vector_record_immutable(self):
        r = VectorRecord(id="x1", vector=[0.1], payload={"k": "v"})
        assert r.id == "x1"
        with pytest.raises(Exception):
            r.id = "x2"

    def test_vector_sink_abstract(self):
        with pytest.raises(TypeError):
            VectorSink()


# ── Scraper base ───────────────────────────────────────────────────────────────

class TestScraperBase:
    def test_source_config(self):
        cfg = SourceConfig(id="r1", type="rss", url="http://x", schedule_cron="*/5 * * * *")
        assert cfg.id == "r1"
        assert cfg.language == "en"
        assert cfg.tags == []
        assert cfg.extra == {}

    def test_source_config_with_options(self):
        cfg = SourceConfig(
            id="r1", type="rss", url="http://x", schedule_cron="*/5 * * * *",
            language="fr", tags=["eco"], extra={"timeout": 60},
        )
        assert cfg.language == "fr"
        assert cfg.tags == ["eco"]
        assert cfg.extra["timeout"] == 60

    def test_news_source_abstract(self):
        with pytest.raises(TypeError):
            NewsSource(SourceConfig(id="t", type="rss", url="u", schedule_cron=""))

    def test_parsing_strategy_abstract(self):
        with pytest.raises(TypeError):
            ParsingStrategy()


# ── Deduplication ──────────────────────────────────────────────────────────────

class TestDeduplication:

    def test_dedup_first_item(self):
        step = DeduplicateStep()
        item = NewsItem(source_id="s", url="http://x")
        assert step.process(item) is not None

    def test_dedup_duplicate_returns_none(self):
        step = DeduplicateStep()
        item = NewsItem(source_id="s", url="http://x")
        step.process(item)
        assert step.process(item) is None

    def test_dedup_different_urls(self):
        step = DeduplicateStep()
        item1 = NewsItem(source_id="s", url="http://x/a")
        item2 = NewsItem(source_id="s", url="http://x/b")
        assert step.process(item1) is not None
        assert step.process(item2) is not None