"""LLM generator (Facade: hides provider differences)."""
from __future__ import annotations

import os
from typing import Protocol

from openai import OpenAI

from src.common.config import get_settings
from src.rag.retriever import RetrievedDoc


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAIGenerator:
    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        self._model = model or s.llm_model
        self._temperature = s.llm_temperature

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model, temperature=self._temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""


def build_context(docs: list[RetrievedDoc]) -> str:
    return "\n\n---\n\n".join(
        f"[{i+1}] {d.title or 'Untitled'}\nURL: {d.url}\n{d.chunk_text}"
        for i, d in enumerate(docs)
    )
