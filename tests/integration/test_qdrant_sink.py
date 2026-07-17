"""Integration test: Qdrant sink validated against running Qdrant server."""

import uuid

import pytest

from src.processors.sinks.qdrant_sink import QdrantSink
from src.processors.sinks.base import VectorRecord


@pytest.mark.integration
def test_qdrant_upsert_roundtrip():
    """Upsert a point to a temporary test collection, verify it returned count=1."""
    test_collection = f"test_integration_{uuid.uuid4().hex[:8]}"
    sink = QdrantSink(url="http://localhost:6333", collection=test_collection)

    # Create a temp collection with small vector size
    sink.ensure_collection(4)

    # Upsert a point
    test_point_id = str(uuid.uuid4())
    n = sink.upsert([
        VectorRecord(
            id=test_point_id,
            vector=[0.1, 0.2, 0.3, 0.4],
            payload={"url": "https://test-integration.example.com"},
        ),
    ])
    assert n == 1

    # Verify the point is there
    results = sink._client.query_points(
        collection_name=test_collection,
        query=[0.1, 0.2, 0.3, 0.4],
        limit=1,
        with_payload=True,
    )
    assert len(results.points) == 1
    assert results.points[0].payload["url"] == "https://test-integration.example.com"

    # Cleanup
    sink._client.delete_collection(test_collection)