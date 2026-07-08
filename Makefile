.PHONY: help up down logs run-scraper run-pipeline rag-api test lint fmt typecheck

help:
	@grep -E '^[a-zA-Z_-]+:.*##' Makefile | awk -F':.*##' '{printf "%-18s %s\n", $$1, $$2}'

up: ## Start all services (Kafka KRaft, Flink, Qdrant, Schema Registry)
	docker compose up -d

down: ## Stop all services
	docker compose down -v

logs: ## Tail logs
	docker compose logs -f --tail=100

run-scraper: ## Run scrapers locally
	python -m src.scrapers.main --config configs/scrapers/sources.yaml

run-pipeline: ## Submit Flink job
	./scripts/run_pipeline.sh

rag-api: ## Start RAG FastAPI server
	uvicorn src.rag.api:app --reload --port 8000

test: ## Run tests
	pytest

lint: ## Lint
	ruff check .

fmt: ## Format
	ruff format .

typecheck: ## Type check
	mypy src
