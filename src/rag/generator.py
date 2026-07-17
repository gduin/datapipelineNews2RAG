"""LLM generators (Facade: hides provider differences)."""
from __future__ import annotations

import os
from typing import Protocol

from openai import OpenAI

from src.common.config import get_settings
from src.rag.retriever import RetrievedDoc


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAIGenerator:
    """Calls an OpenAI (or OpenAI-compatible) chat completions endpoint.

    Works for:
      - OpenAI itself (set OPENAI_API_KEY, leave llm_base_url empty)
      - llama.cpp server (set llm_base_url=http://llama-server:8080/v1,
        OPENAI_API_KEY can be any non-empty string)
    """

    def __init__(self, model: str | None = None, timeout: float | None = None) -> None:
        s = get_settings()
        api_key = os.environ.get("OPENAI_API_KEY", "")
        # llama.cpp server accepts any non-empty key; OpenAI needs a real one.
        # Use a placeholder if the user pointed us at a local base_url and left
        # the key empty so the SDK client doesn't reject outright.
        if not api_key and s.llm_base_url:
            api_key = "sk-no-key-needed-for-local-llamacpp"
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY env var is empty and llm_base_url is unset. "
                "Either provide a real OpenAI key, or set LLM_BASE_URL to point "
                "at a local llama.cpp server (and any non-empty OPENAI_API_KEY)."
            )
        # Use provided timeout, default to 600s (10 min), or fall back to SDK default
        effective_timeout = timeout if timeout is not None else 600.0
        self._client = OpenAI(
            api_key=api_key,
            base_url=s.llm_base_url or None,
            timeout=effective_timeout,
        )
        self._model = model or s.llm_model
        self._temperature = s.llm_temperature

    def complete(self, system: str, user: str) -> str:
        print(system, user)
        resp = self._client.chat.completions.create(
            model=self._model, temperature=self._temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        print(resp)
        return resp.choices[0].message.content or ""


class StubGenerator:
    """No-LLM generator: returns the retrieved context verbatim formatted.

    Useful for offline dev/test and to verify the retriever end-to-end before
    wiring in an actual LLM. The 'answer' it returns is just a concatenated
    digest of the retrieved chunks headed with a stub banner.
    """

    _BANNER = "[stub llm] No LLM was called (LLM_PROVIDER=stub). "
    "Showing retrieved context verbatim."

    def complete(self, system: str, user: str) -> str:
        # The service passes the context embedded into `user`; surface it back
        # annotated, so users can verify what was retrieved.
        return f"{self._BANNER}\n\n{user}"


def build_context(docs: list[RetrievedDoc]) -> str:
    return "\n\n---\n\n".join(
        f"[{i+1}] {d.title or 'Untitled'}\nURL: {d.url}\n{d.chunk_text}"
        for i, d in enumerate(docs)
    )
