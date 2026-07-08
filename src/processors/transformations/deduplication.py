"""URL-based deduplication step (uses Flink keyed state in real job)."""
from __future__ import annotations

from src.processors.base import NewsItemStep
from src.schemas.models import NewsItem


class DeduplicateStep(NewsItemStep):
    """Stateless placeholder; actual dedup done via Flink KeyedProcessFunction."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def process(self, item: NewsItem) -> NewsItem | None:
        if item.url in self._seen:
            return None
        self._seen.add(item.url)
        return item
