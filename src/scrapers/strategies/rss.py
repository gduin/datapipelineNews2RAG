"""RSS/Atom parsing strategy."""
from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from src.scrapers.base import ParsingStrategy, SourceConfig
from src.schemas.models import NewsItem


class RSSParsingStrategy(ParsingStrategy):
    def parse(self, raw: bytes | str, source: SourceConfig) -> list[NewsItem]:
        parsed = feedparser.parse(raw)
        items: list[NewsItem] = []
        for entry in parsed.entries:
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            published_at = (
                datetime(*published[:6], tzinfo=timezone.utc).timestamp()
                if published else None
            )
            items.append(
                NewsItem(
                    source_id=source.id,
                    url=entry.get("link", ""),
                    title=entry.get("title"),
                    summary=entry.get("summary"),
                    content=entry.get("content", [{}])[0].get("value")
                    if entry.get("content") else None,
                    author=entry.get("author"),
                    published_at=int(published_at) if published_at else None,
                    language=source.language,
                    tags=source.tags,
                    fetched_at=int(datetime.now(timezone.utc).timestamp()),
                )
            )
        return items
