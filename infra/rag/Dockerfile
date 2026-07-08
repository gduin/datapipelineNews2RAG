FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn[standard] qdrant-client openai pydantic-settings structlog httpx sentence-transformers
COPY src ./src
COPY configs ./configs
EXPOSE 8000
CMD ["uvicorn","src.rag.api:app","--host","0.0.0.0","--port","8000"]
