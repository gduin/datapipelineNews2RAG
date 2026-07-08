import pytest

pytestmark = pytest.mark.skipif(
    True,  # flip to False when running against a live Qdrant
    reason="Integration test requires Qdrant running",
)


def test_qdrant_upsert_roundtrip():
    from src.processors.sinks.qdrant_sink import QdrantSink
    from src.processors.sinks.base import VectorRecord

    sink = QdrantSink()
    sink.ensure_collection(4)
    n = sink.upsert([
        VectorRecord(id="x1", vector=[0.1, 0.2, 0.3, 0.4], payload={"url": "https://x"}),
    ])
    assert n == 1
