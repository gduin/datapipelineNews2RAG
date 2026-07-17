"""FastAPI endpoint exposing RAG."""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from src.common.logging import configure_logging
from src.processors.embeddings.factory import build_embedder
from src.rag.factory import build_generator
from src.rag.retriever import NewsRetriever
from src.rag.service import RAGService

app = FastAPI(title="News RAG API", version="0.1.0")
configure_logging()


class Question(BaseModel):
    text: str
    top_k: int = 5
    llm_provider: Literal["openai", "anthropic", "stub", "llamacpp"] | None = None
    timeout: float | None = None


class Answer(BaseModel):
    answer: str
    sources: list[str]


def _service(top_k: int = 5, llm_provider: str | None = None, timeout: float | None = None) -> RAGService:
    return RAGService(
        retriever=NewsRetriever(build_embedder()),
        generator=build_generator(provider_override=llm_provider, timeout=timeout),
        top_k=top_k,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=Answer)
def ask(q: Question) -> Answer:
    result = _service(top_k=q.top_k, llm_provider=q.llm_provider, timeout=q.timeout).ask(q.text)
    return Answer(answer=result.answer, sources=result.sources)
