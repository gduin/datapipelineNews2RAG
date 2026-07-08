"""RAG service: ties retrieval + generation (Facade)."""
from __future__ import annotations

from dataclasses import dataclass

from src.rag.generator import LLMClient, build_context
from src.rag.retriever import NewsRetriever


@dataclass
class RagAnswer:
    answer: str
    sources: list[str]


class RAGService:
    def __init__(self, retriever: NewsRetriever, generator: LLMClient, top_k: int = 5) -> None:
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k
        self._system_prompt = (
            "You are a news analyst. Answer user questions using ONLY the provided context. "
            "Cite source URLs. If the context is insufficient, say "
            "\"I don't have enough information.\""
        )

    def ask(self, question: str) -> RagAnswer:
        docs = self._retriever.search(question, top_k=self._top_k)
        if not docs:
            return RagAnswer(answer="I don't have enough information.", sources=[])
        context = build_context(docs)
        user = f"Context:\n{context}\n\nQuestion: {question}"
        answer = self._generator.complete(self._system_prompt, user)
        return RagAnswer(answer=answer, sources=[d.url for d in docs])
