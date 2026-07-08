"""Canonical domain models."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NewsItem:
    source_id: str
    url: str
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: int | None = None
    language: str | None = None
    tags: list[str] = field(default_factory=list)
    fetched_at: int = 0


@dataclass(frozen=True)
class NewsChunk:
    chunk_id: str
    url: str
    title: str | None
    chunk_text: str
    chunk_index: int
    total_chunks: int
    language: str | None
    published_at: int | None
    source_id: str
    tags: list[str]
