FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    confluent-kafka \
    httpx \
    feedparser \
    beautifulsoup4 \
    lxml \
    pydantic-settings \
    structlog \
    pyyaml \
    tenacity

COPY src ./src
COPY configs ./configs
EXPOSE 9000
CMD ["python", "-m", "src.scrapers.main", "--config", "/app/configs/scrapers/sources.yaml"]
