# Deployment

## Prerequisites

- **Docker Engine** 26.x+ and **Docker Compose** v2
- **Git** (optional, for cloning)
- **Hardware recommendations**:
  - Minimum: 8GB RAM, 4 CPU cores (for Flink + sentence-transformers + scraper)
  - For llama.cpp: 16GB+ RAM (12B Q4 model needs ~7.5GB VRAM-equivalent in system RAM)
  - Storage: ~10GB free for Docker images + Qdrant data + Kafka volumes

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd datapipelineNews2RAG

# 2. Configure
cp .env.example .env
# Edit .env — adjust LLM_PROVIDER, LLM_BASE_URL, keys as needed

# 3. Start infrastructure (Kafka KRaft, Schema Registry, Flink, Qdrant, Prometheus, Grafana)
make up


# 4. Start scraper (long-running daemon; produces news to Kafka)
docker compose up -d scraper

# 5. Submit Flink pipeline job
./scripts/run_pipeline.sh

# 6. Start RAG API
make rag-api

# 7. Test
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the market outlook?", "llm_provider": "stub"}'
```

## Component-by-Component Startup

### All Infrastructure (without scraper/pipeline/rag-api)
```bash
docker compose up -d
# Starts: kafka-1/2/3, kafka-init, kafka-ui, schema-registry,
#         flink-jobmanager, flink-taskmanager, qdrant,
#         prometheus, grafana
```

Watch startup:
```bash
docker compose logs -f | grep -E "kafka|flink|qdrant"
# Wait until flink-jobmanager reports (healthy) and kafka brokers report (healthy)
```

### Scraper (News Ingestion)
```bash
docker compose up -d scraper
docker compose logs -f scraper
```
The scraper polls all 9 sources concurrently, rate-limited at 1 request/second. Each feed is polled at its configured interval (5–30 minutes). Articles are JSON-serialized and sent to Kafka topic `news.raw` with idempotent producer guarantees.

**Verify**:
```bash
# Check Kafka topic has messages
docker exec kafka-1 kafka-console-consumer --bootstrap-server kafka-1:9092 --topic news.raw --max-messages 3
# Or use Kafka UI at http://localhost:8118
```

### Flink Pipeline Job
```bash
./scripts/run_pipeline.sh
```
or manually:
```bash
docker compose up -d flink-job
docker compose logs -f flink-job
```

The job (`news-rag-pipeline`) consumes `news.raw`, transforms → chunks → embeds → upserts into Qdrant. Progress is visible via Flink stdout (`stream.print`) and Qdrant point count.

**Verify**:
```bash
# Check Flink job status
curl -s http://localhost:8083/overview | python3 -m json.tool
# Check Qdrant point count
curl -s http://localhost:6333/collections/news_embeddings | python3 -m json.tool | grep points_count
```

### RAG API
```bash
make rag-api
```
Or via Docker:
```bash
docker compose up -d rag-api
docker compose logs rag-api
```

**Verify health**:
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

**Test stub (offline)**:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "test", "llm_provider": "stub"}'
```

### llama-server (Optional, Local LLM)
```bash
docker compose --profile llm up -d llama-server
docker compose logs llama-server
```

Wait for model load. Verify:
```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

Then query with:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Market outlook", "llm_provider": "llamacpp", "timeout": 300.0}'
```

## Full Startup Sequence (Recommended)

```bash
make up                                    # 1. Infrastructure

docker compose up -d scraper              # 2. Ingestion
# Wait 2+ minutes for first articles to accumulate

docker compose up -d flink-job            # 3. Pipeline
# Wait for job RUNNING + first upserts

# (Optional) Start llama-server if using llamacpp
docker compose --profile llm up -d llama-server

# Start RAG API on host or via Docker
docker compose up -d rag-api              # 4. Query API (Docker)
# OR
make rag-api                              # 4. Query API (host, dev mode)
```

Alternatively, run `docker compose up -d` to start EVERYTHING at once (minus llama-server, which requires `--profile llm`).

```bash
docker compose up -d     # Start all services with defaults
```

## Stopping

```bash
docker compose down           # Stop all services, remove containers + networks
docker compose down -v        # Also remove named volumes (Kafka data, Qdrant data, Flink state)
docker compose down -v flink-checkpoints flink-savepoints  # Full data wipe
```

## Configuration

All services read from a single `.env` file at the project root. Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

Key settings you'll likely change:

```env
# LLM provider (required for /ask)
LLM_PROVIDER=llamacpp          # openai | llamacpp | stub
LLM_BASE_URL=http://llama-server:8080/v1   # Required for llamacpp

# Embeddings provider (required for pipeline + /ask)
EMBEDDING_PROVIDER=sentence_transformers   # sentence_transformers | openai
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2  # Model name

# External API keys (if using openai provider)
OPENAI_API_KEY=sk-...

# Rate limiting (scraper)
SCRAPER_RATE_LIMIT_RPS=1       # Requests per second across all sources

# Observability
LOG_LEVEL=INFO                 # DEBUG | INFO | WARNING | ERROR
```

## Observability URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Kafka UI | `http://localhost:8118` | Topic/consumer group inspection |
| Flink Dashboard | `http://localhost:8083` | Job DAG, task metrics, checkpoints |
| Qdrant Dashboard | `http://localhost:6333/dashboard` | Collection stats, vector browser |
| Prometheus | `http://localhost:9090` | Metrics querying |
| Grafana | `http://localhost:3000` | Dashboards (admin/admin) |
| RAG API | `http://localhost:8000` | RAG queries |
| RAG API Docs | `http://localhost:8000/docs` | Interactive OpenAPI (Swagger) |
| llama-server Health | `http://localhost:8080/health` | LLM status |

## Makefile Targets

```bash
make up            # Start all infrastructure services (Docker Compose)
make down          # Stop all services and remove volumes
make logs          # Tail logs from all services
make run-scraper   # Start scraper container (long-running daemon)
make run-pipeline  # Submit Flink job via run_pipeline.sh
make rag-api       # Start RAG FastAPI server on host (uvicorn --reload)
make test          # Run pytest test suite
make lint          # Run ruff linter
make fmt           # Run ruff formatter
make typecheck     # Run mypy type checker
```

## Development Workflow

### Hot Reload for Flink Job
The `./src:/opt/flink-job/src:ro` mount on both JM and TM allows code changes to be picked up without rebuilding images. After editing pipeline Python files:

```bash
docker compose restart flink-jobmanager flink-taskmanager
docker compose up -d flink-job
```

### Rebuilding Images After Code Changes
```bash
docker compose build rag-api     # Rebuild RAG API (COPY src in Dockerfile)
docker compose build scraper     # Rebuild scraper
docker compose build flink-job   # Rebuild Flink job submitter
docker compose build             # Rebuild JM/TM (rare — uses src mount)
```

Force clean rebuild (if cached COPY layer causes stale code):
```bash
docker rmi -f <image-name>:latest
docker compose build --no-cache <service>
docker compose up -d <service>
```

### Adding New RSS Sources
Edit `configs/scrapers/sources.yaml`, add a source block:

```yaml
  - id: my_source
    type: rss
    url: https://example.com/rss.xml
    schedule_cron: "*/15 * * * *"
    language: en
    tags: [finance, custom]
```

Restart the scraper:
```bash
docker compose restart scraper
```

No code changes needed — the scraper reads `sources.yaml` dynamically.

## Scaling

```bash
# Scale Flink TaskManagers
docker compose up -d --scale flink-taskmanager=3

# Scale RAG API (adjust port mapping in docker-compose.yml first)
docker compose up -d --scale rag-api=3

# Scale Kafka (add broker to compose + quorum voters)
# Edit docker-compose.yml, add kafka-4 service block, update KAFKA_CONTROLLER_QUORUM_VOTERS
```

## Troubleshooting

### "NoResourceAvailableException" on Flink job submit
- Check JM/TM running: `docker ps --filter "name=flink"`
- Check RPC address: `FLINK_JOBMANAGER_RPC_ADDRESS=flink-jobmanager` in env
- Ensure task slots available: `curl http://localhost:8083/overview`

### Scraper crash-looping ("ValidationError: ...")
- Likely stale `config.py` in image → rebuild with `docker compose build --no-cache scraper`
- Check `.env` values match `Literal[...]` constraints in `Settings`

### RAG API returning stale code
- Force rebuild: `docker rmi -f news-rag-rag-api && docker compose build --no-cache rag-api`

### LLM timeout with llama.cpp
- Adjust `timeout` in request payload (e.g., `"timeout": 600.0`)
- Check llama-server health: `curl http://localhost:8080/health`
- Consider smaller model or GPU acceleration if inference is too slow

### Qdrant "no collection" errors
- Pipeline `ProcessFunction.open()` calls `ensure_collection()` — it auto-creates
- If manually needed: `curl -X PUT http://localhost:6333/collections/news_embeddings -H "Content-Type: application/json" -d '{"vectors": {"size": 768, "distance": "Cosine"}}'`

### Kafka broker not healthy
- Check KRaft quorum: 3 brokers must be running with correct quorum voter config
- Verify: `docker exec kafka-1 kafka-metadata-quorum --bootstrap-server kafka-1:9092 describe --status`
- If stuck: `docker compose down -v && docker compose up -d` (fresh start with clean volumes)

## Kubernetes Deployment

See `deployment/k8s/` for Helm-style Kubernetes manifests (work in progress). The Docker Compose stack maps naturally to Kubernetes:
- Kafka → Strimzi operator or Confluent for Kubernetes
- Flink → Flink Kubernetes Operator (CRD-based)
- Qdrant → StatefulSet with PVC
- RAG API → Deployment + Service (stateless, horizontal scaling)
- Scraper → Deployment (single replica, pull-based)