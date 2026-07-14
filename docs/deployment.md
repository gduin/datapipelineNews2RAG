# Deployment

## Local
```bash
make up
./scripts/seed_topics.sh
make run-scraper        # scraper container (long-running daemon)
./scripts/run_pipeline.sh
make rag-api
curl localhost:8000/ask -d '{"text":"What is happening?"}' -H 'Content-Type: application/json'
```

The scraper runs as a Docker container (`infra/scrapers/Dockerfile`) and produces to Kafka.
Stop it with `docker compose stop scraper` or `docker compose down scraper`.

## Kubernetes
See `deployment/k8s/` for Helm-style manifests (TODO).

## Backups
- Kafka: rely on replication factor 3.
- Qdrant: snapshot via `qdrant_client.create_snapshot(...)`.
