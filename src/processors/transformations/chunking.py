"""Sentence-aware chunking (ChunkStep)."""
from __future__ import annotations

import hashlib
import re

from src.processors.base import ChunkStep
from src.schemas.models import NewsChunk, NewsItem

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class SentenceChunker(ChunkStep):
    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 64) -> None:
        self._max = max_tokens
        self._overlap = overlap_tokens

    @staticmethod
    def _approx_tokens(text: str) -> int:
        return len(text.split())

    def process(self, item: NewsItem) -> list[NewsChunk] | None:
        text = item.content or item.summary or item.title
        if not text:
            return None

        sentences = _SENTENCE_END.split(text)
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for sent in sentences:
            sent_len = self._approx_tokens(sent)
            if current and current_len + sent_len > self._max:
                chunks.append(" ".join(current))
                # overlap: keep last sentences within overlap budget
                tail: list[str] = []
                acc = 0
                for s in reversed(current):
                    if acc + self._approx_tokens(s) > self._overlap:
                        break
                    tail.insert(0, s)
                    acc += self._approx_tokens(s)
                current = tail + [sent]
                current_len = acc + sent_len
            else:
                current.append(sent)
                current_len += sent_len

        if current:
            chunks.append(" ".join(current))

        return [
            NewsChunk(
                chunk_id=hashlib.sha1(f"{item.url}#{i}".encode()).hexdigest(),
                url=item.url,
                title=item.title,
                chunk_text=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                language=item.language,
                published_at=item.published_at,
                source_id=item.source_id,
                tags=item.tags,
            )
            for i, chunk in enumerate(chunks)
        ]
