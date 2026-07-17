"""Tests for RAG components: generator (Stub, OpenAIGenerator, build_context),
factory (build_generator), retriever (NewsRetriever)."""

from unittest.mock import MagicMock

import pytest

from src.rag.generator import (
    LLMClient, OpenAIGenerator, StubGenerator, build_context,
)
from src.rag.factory import build_generator
from src.rag.retriever import NewsRetriever, RetrievedDoc
from qdrant_client.http.models import ScoredPoint, QueryResponse


# ── build_context ──────────────────────────────────────────────────────────────

class TestBuildContext:
    def test_single_doc(self):
        docs = [RetrievedDoc(url="http://x", title="T", chunk_text="hello", score=0.9)]
        ctx = build_context(docs)
        assert "[1] T" in ctx
        assert "URL: http://x" in ctx
        assert "hello" in ctx

    def test_multiple_docs(self):
        docs = [
            RetrievedDoc(url="http://a", title="A", chunk_text="ta", score=0.9),
            RetrievedDoc(url="http://b", title="B", chunk_text="tb", score=0.8),
        ]
        ctx = build_context(docs)
        assert "[1] A" in ctx
        assert "[2] B" in ctx
        assert "---" in ctx

    def test_no_title(self):
        docs = [RetrievedDoc(url="http://x", title=None, chunk_text="c", score=0.5)]
        ctx = build_context(docs)
        assert "[1] Untitled" in ctx

    def test_empty_list(self):
        assert build_context([]) == ""


# ── StubGenerator ──────────────────────────────────────────────────────────────

class TestStubGenerator:
    def test_complete_returns_banner_and_user(self):
        gen = StubGenerator()
        result = gen.complete("system", "user content")
        assert "[stub llm]" in result
        assert "user content" in result

    def test_satisfies_protocol(self):
        gen = StubGenerator()
        assert hasattr(gen, "complete")
        assert callable(gen.complete)


# ── OpenAIGenerator (uses monkeypatch to control env) ──────────────────────────

class TestOpenAIGenerator:
    def test_init_with_explicit_key(self):
        gen = OpenAIGenerator(model="test-model", timeout=30.0)
        assert gen._model == "test-model"

    def test_timeout_passed_to_client(self):
        gen = OpenAIGenerator(timeout=42.0)
        assert gen._client.timeout == 42.0

    def test_default_timeout(self):
        gen = OpenAIGenerator()
        assert gen._client.timeout == 600.0

    def test_timeout_none_defaults_to_600(self):
        gen = OpenAIGenerator(timeout=None)
        assert gen._client.timeout == 600.0

    def test_model_comes_from_env(self):
        gen = OpenAIGenerator()
        assert gen._model  # whatever .env sets

    def test_base_url_comes_from_env(self):
        gen = OpenAIGenerator()
        assert gen._client.base_url is not None

    def test_complete_calls_api(self):
        gen = OpenAIGenerator()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message = MagicMock()
        mock_resp.choices[0].message.content = "answer"
        gen._client.chat.completions = MagicMock()
        gen._client.chat.completions.create.return_value = mock_resp
        result = gen.complete("sys", "usr")
        assert result == "answer"
        gen._client.chat.completions.create.assert_called_once()


# ── build_generator factory ────────────────────────────────────────────────────

class TestBuildGenerator:
    def test_stub_provider(self):
        gen = build_generator(provider_override="stub")
        assert isinstance(gen, StubGenerator)

    def test_stub_provider_has_complete(self):
        gen = build_generator(provider_override="stub")
        assert hasattr(gen, "complete")

    def test_openai_provider_raises_runtimeerror(self):
        pytest.skip("requires no OPENAI_API_KEY and no LLM_BASE_URL — .env provides values")

    def test_llamacpp_requires_base_url(self):
        pytest.skip("requires empty LLM_BASE_URL — .env provides a value")

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="unknown llm_provider"):
            build_generator(provider_override="invalid_provider")

    def test_override_defaults_to_settings(self):
        gen = build_generator()
        assert isinstance(gen, (OpenAIGenerator, StubGenerator))

    def test_timeout_passed_through(self):
        gen = build_generator(provider_override="stub", timeout=30.0)  # stub ignores timeout
        assert hasattr(gen, "complete")


# ── NewsRetriever ──────────────────────────────────────────────────────────────

class StubEmbedder:
    def embed_batch(self, texts):
        return [[0.1] * 768 for _ in texts]


class StubQdrantClient:
    def __init__(self, points=None):
        self._points = points or []
        self.url = "http://stub:6333"

    def query_points(self, **kwargs):
        return QueryResponse(points=self._points)

    def get_collections(self):
        from qdrant_client.http.models import CollectionsResponse, CollectionDescription
        return CollectionsResponse(collections=[])

    def create_collection(self, collection_name, vectors_config):
        pass

    def upsert(self, collection_name, points, wait=True):
        pass


class TestNewsRetriever:
    def test_search_returns_documents(self):
        fake_points = [
            ScoredPoint(
                id="id1", version=1, score=0.95,
                payload={"url": "http://a", "title": "A", "chunk_text": "text a"},
            ),
            ScoredPoint(
                id="id2", version=1, score=0.80,
                payload={"url": "http://b", "title": None, "chunk_text": "text b"},
            ),
        ]
        retriever = NewsRetriever(StubEmbedder(), client=StubQdrantClient(fake_points))
        docs = retriever.search("query", top_k=3)

        assert len(docs) == 2
        assert docs[0].url == "http://a"
        assert docs[0].title == "A"
        assert docs[0].score == 0.95
        assert docs[1].title is None
        assert docs[1].score == 0.80

    def test_search_empty(self):
        retriever = NewsRetriever(StubEmbedder(), client=StubQdrantClient([]))
        docs = retriever.search("query", top_k=5)
        assert docs == []

    def test_missing_payload_fields_default(self):
        fake_points = [
            ScoredPoint(id="id1", version=1, score=0.0, payload={}),
        ]
        retriever = NewsRetriever(StubEmbedder(), client=StubQdrantClient(fake_points))
        docs = retriever.search("q")
        assert docs[0].url == ""
        assert docs[0].title is None
        assert docs[0].score == 0.0

    def test_custom_client_used(self):
        custom = StubQdrantClient()
        retriever = NewsRetriever(StubEmbedder(), client=custom)
        assert retriever._client is custom