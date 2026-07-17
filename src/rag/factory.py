"""LLM generator factory (mirrors src.processors.embeddings.factory)."""
from __future__ import annotations

import logging

from src.common.config import get_settings
from src.rag.generator import LLMClient, OpenAIGenerator, StubGenerator

log = logging.getLogger(__name__)


def build_generator(provider_override: str | None = None, timeout: float | None = None) -> LLMClient:
    """Build the LLM client based on Settings.llm_provider or override.
    
    Args:
        provider_override: Optional provider to use instead of Settings.llm_provider.
                          Useful for per-request provider selection via API.
        timeout: Optional timeout in seconds for LLM API calls. Defaults to 600s.
    """
    s = get_settings()
    provider = provider_override or s.llm_provider
    log.info(
        "building_llm provider=%s model=%s base_url=%s timeout=%s",
        provider, s.llm_model, s.llm_base_url or "<default>", timeout,
    )
    match provider:
        case "openai":
            return OpenAIGenerator(timeout=timeout)
        case "llamacpp":
            if not s.llm_base_url:
                raise RuntimeError(
                    "LLM_PROVIDER=llamacpp requires LLM_BASE_URL to be set "
                    "(e.g. http://llama-server:8080/v1)"
                )
            return OpenAIGenerator(timeout=timeout)
        case "stub":
            return StubGenerator()
        case _:
            raise ValueError(f"unknown llm_provider: {provider!r}")
