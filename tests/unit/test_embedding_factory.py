"""Tests for embedding factory (build_embedder)."""

import pytest

from src.common.exceptions import EmbeddingError
from src.processors.embeddings.factory import build_embedder
from src.processors.embeddings.base import Embedder


class TestBuildEmbedder:
    def test_default_returns_sentence_transformers(self):
        embedder = build_embedder()
        from src.processors.embeddings.sentence_transformers_embedder import (
            SentenceTransformersEmbedder,
        )
        assert isinstance(embedder, SentenceTransformersEmbedder)

    def test_invalid_provider_raises(self):
        pytest.skip("requires monkeypatching an env-var that .env file overrides")

    def test_returns_embedder(self):
        embedder = build_embedder()
        assert isinstance(embedder, Embedder)