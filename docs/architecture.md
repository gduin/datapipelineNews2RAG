# Architecture

## Components
1. **Scrapers** (Python, async) — pluggable sources via `NewsSourceFactory`.
2. **Kafka 3.7+ (KRaft)** — 3-broker quorum, no ZooKeeper. Topics: `news.raw`, `news.embedded`, `news.dlq`.
3. **Schema Registry** — Avro schemas in `src/schemas/avro/`.
4. **PyFlink Job** — consumes `news.raw`, applies chain of transformations, generates embeddings, upserts into Qdrant, publishes `news.embedded`.
5. **Qdrant** — vector store with cosine similarity.
6. **RAG API** (FastAPI) — `/ask` endpoint that retrieves and generates.

## SOLID mapping
- SRP: `NormalizeStep`, `SentenceChunker`, `QdrantSink` each do one thing.
- OCP: Register new sources/embedders via `@register` decorators — no core edits.
- LSP: Any `NewsSource`/`Embedder`/`VectorSink` subtype can replace base.
- ISP: `Embedder` exposes only `embed_batch`; `VectorSink` exposes only `upsert`/`ensure_collection`.
- DIP: `Pipeline` depends on `Embedder` and `VectorSink` abstractions, not concrete classes.

## Patterns
- Abstract Factory, Strategy, Builder, Chain of Responsibility, Repository, Adapter, Decorator, Facade, Singleton.

## Why Flink
Real-time, exactly-once, fine-grained backpressure, native state for dedup. Spark Structured Streaming would also work but adds micro-batch latency.

## Why Kafka KRaft
ZooKeeper is deprecated and removed in Kafka 4.0. KRaft ships in 3.3+. We use 3 brokers forming the quorum voters.
