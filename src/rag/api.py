"""FastAPI endpoint exposing RAG."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from src.common.logging import configure_logging
from src.processors.embeddings.factory import build_embedder
from src.rag.generator import OpenAIGenerator
from src.rag.retriever import NewsRetriever
from src.rag.service import RAGService

app = FastAPI(title="News RAG API", version="0.1.0")
configure_logging()


class Question(BaseModel):
    text: str
    top_k: int = 5


class Answer(BaseModel):
    answer: str
    sources: list[str]


def _service() -> RAGService:
    return RAGService(
        retriever=NewsRetriever(build_embedder()),
        generator=OpenAIGenerator(),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=Answer)
def ask(q: Question) -> Answer:
    result = _service().ask(q.text)
    return Answer(answer=result.answer, sources=result.sources)
