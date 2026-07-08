import pytest

pytestmark = pytest.mark.skipif(
    True, reason="E2E test requires docker compose stack running",
)


def test_end_to_end():
    # 1. produce a news item to news.raw
    # 2. run pipeline (Flink or local orchestrator)
    # 3. query RAG API
    # 4. assert non-empty answer
    pytest.fail("Implement once stack is up")
