# News RAG Pipeline

Real-time news ingestion → Kafka → PyFlink → Embeddings → Qdrant → RAG.

## Architecture
```
[Scrapers] -> [Kafka KRaft] -> [PyFlink Job] -> [Qdrant]
                                    |               |
                                    v               v
                              [Schema Registry] [LLM RAG API]
```

## Quickstart
```bash
make up            # spin up Kafka (KRaft), Flink, Qdrant, Schema Registry
make run-scraper   # launch RSS scrapers
make run-pipeline  # submit Flink job
make rag-api       # start FastAPI RAG endpoint
make test
```

See `docs/architecture.md` for the full design.
