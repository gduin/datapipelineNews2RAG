from src.rag.generator import LLMClient
from src.rag.retriever import NewsRetriever, RetrievedDoc
from src.rag.service import RAGService


class StubRetriever(NewsRetriever):
    def __init__(self, docs: list[RetrievedDoc]) -> None:
        self._docs = docs
    def search(self, query: str, top_k: int = 5):  # type: ignore[override]
        return self._docs


class StubGenerator(LLMClient):
    def __init__(self, text: str = "stub-answer") -> None:
        self._text = text
    def complete(self, system: str, user: str) -> str:  # type: ignore[override]
        return self._text


def test_rag_returns_answer_with_sources():
    docs = [RetrievedDoc(url="https://x", title="T", chunk_text="c", score=0.9)]
    svc = RAGService(StubRetriever(docs), StubGenerator("Hello!"))
    res = svc.ask("anything")
    assert res.answer == "Hello!"
    assert res.sources == ["https://x"]


def test_rag_no_docs():
    svc = RAGService(StubRetriever([]), StubGenerator())
    res = svc.ask("nothing here")
    assert "don't have enough" in res.answer.lower()
