# Deployment

## Local
```bash
make up
./scripts/seed_topics.sh
./scripts/run_scraper.sh (or) python -m src.scrapers.main --config configs/scrapers/sources.yaml
./scripts/run_pipeline.sh
make rag-api
curl localhost:8000/ask -d '{"text":"What is happening?"}' -H 'Content-Type: application/json'
```

## Kubernetes
See `deployment/k8s/` for Helm-style manifests (TODO).

## Backups
- Kafka: rely on replication factor 3.
- Qdrant: snapshot via `qdrant_client.create_snapshot(...)`.
