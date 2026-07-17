"""End-to-end test: produce to Kafka → Flink processes → Qdrant has point → RAG API answers.

Requires full docker compose stack running.
Run with: python -m pytest tests/e2e/test_pipeline_e2e.py -v --tb=short -m e2e --no-cov
"""

import json
import time
import uuid

import pytest
import requests

from src.common.config import Settings

KAFKA_CONTAINER = "kafka-1"
KAFKA_BOOTSTRAP = "kafka-1:9092"
RAG_API_URL = "http://localhost:8000/ask"


def _ensure_docker_exec() -> bool:
    import subprocess
    try:
        subprocess.run(["docker", "ps"], capture_output=True, check=True)
        return True
    except Exception:
        return False


@pytest.mark.e2e
class TestPipelineEndToEnd:

    def test_produce_to_qdrant_to_rag(self):
        """Produce a news article → wait for Flink to process → verify in Qdrant → query RAG."""
        if not _ensure_docker_exec():
            pytest.skip("Docker not available")

        settings = Settings()
        unique_url = f"https://e2e-test.example.com/{uuid.uuid4().hex}"

        # 1. Produce a news item to Kafka
        article = json.dumps({
            "source_id": "e2e_test",
            "url": unique_url,
            "title": "E2E Test: Global Semiconductor Shortage Easing",
            "summary": "Chip makers report improved supply chains",
            "content": (
                "The global semiconductor shortage that plagued industries from automotive "
                "to consumer electronics is finally showing signs of easing. Taiwan Semiconductor "
                "Manufacturing Company reported record production output in Q2 2026. "
                "Samsung Electronics and Intel have both brought new fabrication plants online. "
                "Industry analysts project that supply-demand balance will normalize by Q4 2026. "
                "However, geopolitical risks remain as key materials are sourced from regions "
                "with ongoing trade tensions."
            ),
            "author": "Test Author",
            "published_at": int(time.time()),
            "language": "en",
            "tags": ["technology", "semiconductors", "business"],
            "fetched_at": int(time.time()),
        })

        import subprocess
        cmd = [
            "docker", "exec", KAFKA_CONTAINER,
            "kafka-console-producer",
            "--bootstrap-server", KAFKA_BOOTSTRAP,
            "--topic", settings.kafka_news_topic,
        ]
        proc = subprocess.run(cmd, input=article, capture_output=True, text=True, timeout=15)
        assert proc.returncode == 0, f"Kafka produce failed: {proc.stderr}"

        # 2. Wait for Flink to process (up to 30 seconds)
        from src.processors.embeddings.factory import build_embedder
        embedder = build_embedder()
        query_vector = embedder.embed_batch(
            ["semiconductor shortage production supply chain"]
        )[0]

        found = False
        for _ in range(15):
            from qdrant_client import QdrantClient
            qc = QdrantClient(url="http://localhost:6333")
            results = qc.query_points(
                collection_name=settings.qdrant_collection,
                query=query_vector,
                limit=5,
                with_payload=True,
            )
            for p in results.points:
                if p.payload.get("url") == unique_url:
                    found = True
                    break
            if found:
                break
            time.sleep(2)

        assert found, (
            f"Article {unique_url} not found in Qdrant after 30s. "
            "Check Flink job status and logs."
        )

        # 3. Query RAG API with stub provider (offline, instant answer)
        resp = requests.post(
            RAG_API_URL,
            json={
                "text": "What is happening with the semiconductor supply chain?",
                "top_k": 5,
                "llm_provider": "stub",
            },
            timeout=30,
        )
        assert resp.status_code == 200, f"RAG API returned {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["sources"], list)
        # Our article should be among the sources
        assert unique_url in data["sources"], (
            f"Test article URL not in sources. Sources: {data['sources']}"
        )
        assert "stub llm" in data["answer"] or "semiconductor" in data["answer"].lower()

    def test_rag_health(self):
        """Verify /health endpoint responds."""
        resp = requests.get("http://localhost:8000/health", timeout=10)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"