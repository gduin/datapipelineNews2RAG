# Architecture

## System Overview

The News2RAG pipeline is a real-time data engineering system that ingests financial and economic news, processes it through a streaming pipeline, and exposes a Retrieval-Augmented Generation (RAG) API for question answering over the collected corpus.

## Component Architecture

### 1. Ingestion Layer: Scrapers
- **Runtime**: Python 3.11, async/await (asyncio)
- **Sources**: 9 RSS feeds from Reuters, CNBC, WSJ, MarketWatch, Yahoo Finance, Investing.com, The Economist, Forbes
- **Scheduler**: `NewsScheduler` polls each source at configurable intervals with rate limiting (`asyncio.Semaphore`)
- **Output**: JSON-serialized `NewsItem` records → Kafka topic `news.raw` (keyed by URL, idempotent producer)
- **Resilience**: Exponential backoff with `tenacity`, graceful shutdown on SIGINT/SIGTERM, structured logging per source

### 2. Message Backbone: Kafka KRaft (Confluent 7.6.1)
- **Topology**: 3-broker controller quorum (Kafka 3.7+ native KRaft mode, no ZooKeeper)
- **Topics**: `news.raw` (12 partitions), `news.embedded`, `news.dlq`
- **Partitions**: 12 for `news.raw` — enables parallel consumption by up to 12 Flink task slots
- **Config**: `enable.idempotence=true`, `acks=all`, `compression.type=zstd`
- **Health**: Each broker has a 15s interval healthcheck (`kafka-broker-api-versions`), 10 retries
- **UI**: Kafka UI on port 8118 for topic/consumer group inspection

### 3. Schema Layer: Schema Registry (Confluent 7.6.1)
- **Schemas**: Avro definitions for `news_raw` and `news_embedded` in `src/schemas/avro/`
- **Purpose**: Enables schema evolution without breaking downstream consumers
- **Port**: 8081 (internal)

### 4. Stream Processing: PyFlink 1.18.1
- **Cluster**: Flink 1.18.1 Java 17 — 1 JobManager + 1 TaskManager (2 task slots)
- **Job**: `news-rag-pipeline`, Python-only implementation
- **Source**: `KafkaSource` with `SimpleStringSchema` deserialization, consumer group `flink-rag-pipeline`
- **ProcessFunction** pipeline (per-message, stateless):
  1. **Decode**: Handles Row, list, dict, string, and JSON input formats
  2. **Validate**: Pydantic `NewsItem` schema validation — rejects invalid messages silently
  3. **Normalize**: `NormalizeStep` — text cleaning, whitespace, encoding
  4. **Chunk**: `SentenceChunker` — sentence-aware splitting, max 512 tokens, 64-token overlap
  5. **Embed**: `build_embedder()` dispatches to `SentenceTransformersEmbedder` (all-mpnet-base-v2, 768-dim vectors, local inference) or `OpenAIEmbedder`
  6. **Sink**: `QdrantSink.upsert()` — deterministic UUID chunk IDs (SHA1 of `url#chunk_index`, hexdigest[:32] → UUID)
- **Fault Tolerance**: Exactly-once semantics, RocksDB state backend, periodic checkpoints, savepoints
- **Debugging**: `stream.print("news-stream")` for ingest visibility

### 5. Vector Store: Qdrant 1.10.1
- **Collection**: `news_embeddings`, vector size 768, Cosine distance
- **Storage**: Named Docker volume `qdrant-data` (persistent)
- **gRPC**: Port 6334 (internal), HTTP: 6333
- **Client**: `qdrant-client` 1.18.0 with `query_points(query=vector, with_payload=True)`

### 6. RAG API: FastAPI (Python 3.11)
- **Endpoints**:
  - `GET /health` → `{"status": "ok"}`
  - `POST /ask` → accepts `Question(text, top_k=5, llm_provider?, timeout?)` → returns `Answer(answer, sources[])`
- **Query pipeline**:
  1. Embed user question via same sentence-transformers model (768-dim)
  2. Cosine similarity search in Qdrant via `query_points(limit=top_k)`
  3. Build context block from retrieved chunks (`[n] title\nURL: ...\ntext`)
  4. Send system prompt + context + question to LLM
- **LLM Providers** (selectable per-request via `llm_provider` field):
  - `openai` — OpenAI API (requires `OPENAI_API_KEY`)
  - `llamacpp` — Local llama.cpp server exposing OpenAI-compatible `/v1` endpoint (requires `LLM_BASE_URL`)
  - `stub` — No LLM; returns retrieved context verbatim (offline dev/testing)
- **Timeout**: Configurable per-request (`timeout` field in seconds, defaults to 600s / 10min for local models)
- **Generator**: `OpenAIGenerator` wraps `openai.OpenAI()` client with configurable `base_url` and `timeout`; `StubGenerator` for offline testing

### 7. Optional: llama-server
- **Image**: `ghcr.io/ggml-org/llama.cpp:server`
- **Profile**: `["llm"]` — starts only with `docker compose --profile llm up`
- **Models**: GGUF files mounted from host read-only at `/models`
- **API**: OpenAI-compatible chat completions at `/v1/chat/completions`
- **Current model**: `gemma-4-12b-it-UD-Q4_K_XL.gguf` (12B params, 7.35GB, CPU-only inference)

### 8. Observability
- **Prometheus**: v2.53.0, port 9090 — scrapes Flink JM, Qdrant, and RAG API every 15s
- **Grafana**: v11.1.0, port 3000 — admin/admin, manual dashboard setup
- **Structured Logging**: `structlog` with ISO timestamps, log levels, context variables, console renderer; configured in `ProcessFunction.open()` and at service startup

---

## Software Engineering Best Practices

### Design Principles (SOLID)

| Principle | Implementation |
|-----------|---------------|
| **S — Single Responsibility** | `NormalizeStep`, `SentenceChunker`, `QdrantSink` each perform exactly one transformation. `NewsRetriever` handles only retrieval; `OpenAIGenerator` handles only LLM calls. |
| **O — Open/Closed** | Extend via factory registration (`build_embedder()`, `build_generator()`) — add new providers without modifying core pipeline code. New RSS sources added in `sources.yaml` with zero code changes. |
| **L — Liskov Substitution** | Any `Embedder`, `VectorSink`, or `LLMClient` subtype can replace its base protocol. Stub implementations satisfy the same contracts. |
| **I — Interface Segregation** | `Embedder` exposes only `embed_batch` + `embed_chunk`; `VectorSink` exposes only `upsert` + `ensure_collection`; `LLMClient` Protocol defines only `complete()`. No fat interfaces. |
| **D — Dependency Inversion** | Pipeline depends on `Embedder` and `VectorSink` abstractions, not concrete classes. `RAGService` accepts `LLMClient` Protocol, not specific generator. Factory functions inject implementations. |

### Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Abstract Factory** | `build_embedder()`, `build_generator()`, `NewsSourceFactory` | Decouple provider selection from pipeline logic |
| **Strategy** | `Embedder` subtypes, `LLMClient` subtypes, scraping strategies (RSS/HTML) | Swap algorithms at runtime |
| **Builder** | `PipelineBuilder.build()` | Construct complex KafkaSource → DataStream topology |
| **Chain of Responsibility** | Normalize → Chunk → Embed → Sink in `ProcessFunction.map()` | Sequential processing pipeline |
| **Repository** | `NewsRetriever` (Qdrant client encapsulated) | Abstract vector store access |
| **Adapter** | `OpenAIGenerator` wraps OpenAI SDK + llama.cpp OpenAI-compatible API | Unified interface over heterogeneous LLM backends |
| **Facade** | `RAGService` ties retriever + generator + context builder | Simplified /ask interface |
| **Singleton** | `@lru_cache(maxsize=1)` on `get_settings()` | Single pydantic-settings instance per process |
| **Observer** | Prometheus metrics scraping + structured logging | Centralized monitoring |

### Code Quality
- **Type hints**: `from __future__ import annotations` throughout; Pydantic models for config validation
- **Static analysis**: `ruff` linting + formatting, `mypy` type checking via Makefile targets
- **Testing**: Unit tests (`test_chunking.py`, `test_cleaning.py`, `test_factory.py`, `test_rag_service.py`), integration tests (`test_qdrant_sink.py`), E2E tests (`test_pipeline_e2e.py`)
- **CI**: GitHub Actions workflow in `.github/workflows/ci.yml`
- **Documentation**: API docs (FastAPI auto-generated OpenAPI at `/docs`), architecture docs, ASCII diagrams

---

## High Availability

### Data Pipeline Resilience

| Component | HA Strategy |
|-----------|-------------|
| **Kafka KRaft** | 3-broker quorum — tolerates 1 broker failure. `acks=all` + `min.insync.replicas=1` for durability vs throughput tradeoff. Replication factor 3 on offsets topic. |
| **Flink JobManager** | Healthcheck (curl `/overview`, 15s/5s/10 retries) enables Docker restart. RocksDB checkpointing enables fast recovery on restart. |
| **Flink TaskManager** | `restart: on-failure` + 2 task slots for parallel processing. RocksDB state persistence on named volume `flink-checkpoints`. |
| **Flink Job** | Exactly-once semantics via checkpoints. `flink-checkpoints` + `flink-savepoints` volumes preserve state across restarts. |
| **Kafka Producer** | Idempotent producer (`enable.idempotence=true`) with retries prevents duplicates on broker failure. |
| **Scraper** | `restart: on-failure` in Docker Compose. Exponential backoff (`tenacity`) on transient HTTP errors. Graceful shutdown preserves in-flight messages. |
| **Qdrant** | Named volume `qdrant-data` persists vectors across restarts. Collection auto-creation in `ensure_collection()` on cold start. |
| **RAG API** | Stateless — can be horizontally scaled behind a load balancer. Singleton `get_settings()` reduces config I/O overhead. |

### Service Dependencies

- **depends_on with health conditions**: `kafka-init` waits on healthy kafka-1; `scraper` waits on healthy kafka-1,2,3; `flink-job` waits on healthy JM + started scraper
- **Graceful degradation**: `/ask` with `llm_provider=stub` returns context without LLM (offline mode); pipeline drops invalid messages silently (no crash-loop)
- **Network isolation**: All services on `news-rag-net` bridge network — inter-service communication via Docker DNS

---

## Maintainability

### Configuration Management
- **Single source of truth**: `.env` file (+ `.env.example` as documentation) with 40+ env vars covering all components
- **Runtime overrides**: `Question` model accepts `top_k`, `llm_provider`, `timeout` per-request
- **Auto-loading**: `pydantic-settings` auto-loads `.env` via `SettingsConfigDict(env_file=".env")`
- **Default fallbacks**: Every Settings field has a production-ready default value

### Separation of Concerns

```
src/
├── common/        — shared config, logging, exceptions (cross-cutting)
├── pipeline/      — Flink job builder + ProcessFunction (stream processing)
├── processors/
│   ├── embeddings/ — Embedder ABC + factory + provider implementations
│   ├── transformations/ — chunking, cleaning, deduplication (pure data transforms)
│   └── sinks/     — VectorSink ABC + QdrantSink implementation
├── rag/           — FastAPI app, retriever, generator, factory, service (query side)
├── scrapers/      — scheduler, base, factory, RSS strategy, HTTP strategy (ingestion)
├── schemas/       — Pydantic + Avro data models (validation)
└── producers/     — Kafka producer abstraction
```

Each domain has its own directory, factories decouple implementations from consumers, and all business logic lives in dedicated step classes.

### DevOps
- **Makefile**: `up`, `down`, `logs`, `run-scraper`, `run-pipeline`, `rag-api`, `test`, `lint`, `fmt`, `typecheck`
- **Docker Compose**: Single-file stack — no complex orchestration tooling required for local dev
- **Hot Reload**: `./src:/opt/flink-job/src:ro` mounts on JM/TM for dev-time code changes; rag-api rebuilds from source on `docker compose build`
- **Image Versioning**: `flink:1.18.1-java17` pinned; CP Kafka 7.6.1 pinned; all Python deps in `requirements.txt` pinned

---

## Reliability

### Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **Kafka Consumer (Flink)** | `SimpleStringSchema` — raw passthrough; decode errors handled at ProcessFunction level |
| **Kafka Producer (Scraper)** | Idempotent producer with `acks=all`; structured logging on send status |
| **Pipeline (ProcessFunction)** | Per-message: catch → log error → return None (drop silently, no crash). DLQ topic `news.dlq` defined but not yet wired. |
| **Scraper HTTP** | `tenacity` with exponential backoff: 3 retries, 5s initial backoff. 404s/5xx logged as errors per source, not fatal. |
| **RAG API** | LLM timeout configurable per-request. Stub provider returns context when LLM unavailable. Graceful HTTP error responses via FastAPI exception handling. |
| **Flink Cluster** | RocksDB state backend with checkpoints enables recovery. Named volumes for checkpoint/savepoint persistence. Exactly-once delivery guarantees. |

### Data Integrity
- **Idempotent writes**: Kafka keyed by article URL; Qdrant point IDs are deterministic SHA1 UUIDs — same article re-ingested = same point overwritten, no duplicates
- **Schema validation**: `NewsItem(**item_dict)` Pydantic validation on every message; malformed messages logged + dropped
- **Collection insurance**: `QdrantSink.ensure_collection()` called in `open()` — collection exists before any upsert attempt
- **Type safety**: Pydantic models define exact schemas for `NewsItem`, `NewsChunk`, `VectorRecord`, `Question`, `Answer`

### Observability
- **Health endpoints**: `/health` on RAG API; `/health` on llama-server; `/overview` on Flink JM (used for Docker healthcheck too)
- **Structured logging**: Every significant event logged with `structlog` — sources fetched, messages processed, upserts performed, failures detected
- **Metrics**: Prometheus scrapes Flink (job/task/slot metrics), Qdrant (collection stats), RAG API (request metrics)
- **Visibility**: Kafka UI (port 8118) — inspect topics, consumer groups, lag, messages in real time

---

## Scalability

### Horizontal Scaling

| Component | How to Scale |
|-----------|--------------|
| **Kafka** | Add brokers to quorum (KRaft supports odd-numbered, up to N). Increase partition count for higher parallelism. |
| **Flink** | Add TaskManagers (`docker compose up -d --scale flink-taskmanager=3`). Increase `TASK_SLOTS` env var. FlinkSource distributes 12 partitions across available slots. |
| **Qdrant** | Qdrant supports clustering (Raft consensus). Add nodes; client connects to any node. |
| **RAG API** | Stateless FastAPI — run multiple instances behind nginx/HAProxy. `docker compose up -d --scale rag-api=3` + port mapping adjustment. |
| **Scrapers** | Add more RSS sources in `sources.yaml` (zero code change). Each source runs as independent async task. Rate limiting (`asyncio.Semaphore`) prevents overwhelm. |

### Vertical/Config Tuning

| Config | Current | Scaling Guidance |
|--------|---------|------------------|
| `news.raw` partitions | 12 | Increase to match TaskManager parallelism |
| Task slots per TM | 2 | Increase for CPU-bound (embedding inference) workloads |
| Flink JM memory | 2048m process | Increase with `jobmanager.memory.process.size` |
| Sentence chunk max tokens | 512 | Tune for embedding model context window |
| Embedding model | all-mpnet-base-v2 (768d) | Swap to larger model (1024d) via `EMBEDDING_MODEL` env var |
| `/ask` top_k | 5 (default) | Configurable per-request; trade recall vs token cost |
| Qdrant vector size | 768 | Must match embedding model; auto-checked vs configured `QDRANT_VECTOR_SIZE` |

### Performance Optimizations Implemented

- **Kafka compression**: `zstd` — high compression ratio, good speed
- **Batch embedding**: `embed_batch(texts)` called per article (not per chunk, but chunks of same article batched)
- **Lazy init**: `ProcessFunction.open()` instantiates Normalize, Chunker, Embedder, Sink once — reused across all messages
- **Model caching**: `SentenceTransformersEmbedder` loads model once; PyFlink passes instance via `open()` context
- **Deterministic IDs**: SHA1 hashing avoids Qdrant upsert conflicts, enables idempotent re-processing
- **Rate limiting**: `asyncio.Semaphore` on scrapers prevents source bans
- **RocksDB state**: Checkpoints avoid full re-processing on restart

---

## External Dependencies

| System | Version | Role |
|--------|---------|------|
| Docker Engine | 26.x+ | Container runtime |
| Docker Compose | v2 | Orchestration |
| Flink | 1.18.1 Java 17 | Stream processing engine |
| Apache Kafka | 7.6.1 (Confluent) | Message broker |
| Schema Registry | 7.6.1 (Confluent) | Schema governance |
| Qdrant | 1.10.1 | Vector database |
| Prometheus | 2.53.0 | Metrics collection |
| Grafana | 11.1.0 | Dashboards |
| llama.cpp | server (latest) | Local LLM inference (optional) |
| Python | 3.11 (slim) | Application runtime |
| PyFlink | 1.18.1 | Python Flink bindings |
| sentence-transformers | 3.0.0 | Embedding model inference |
| transformers (HF) | 4.41.2 | Model loading (pinned for Py 3.10 compat) |