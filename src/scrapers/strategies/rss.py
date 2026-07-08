"""Enhanced RSS/Atom parsing strategy."""
from __future__ import annotations

from datetime import datetime, timezone
from time import mktime

import feedparser
from bs4 import BeautifulSoup

from src.scrapers.base import ParsingStrategy, SourceConfig
from src.schemas.models import NewsItem


class RSSParsingStrategy(ParsingStrategy):
    """Parses RSS feeds and strips HTML from content/summaries."""

    @staticmethod
    def _clean_html(raw_html: str | None) -> str | None:
        if not raw_html:
            return None
        soup = BeautifulSoup(raw_html, "lxml")
        text = soup.get_text(" ", strip=True)
        return text or None

    @staticmethod
    def _extract_content(entry) -> str | None:
        # Try common full-content fields before falling back to summary
        if entry.get("content"):
            content_list = entry.get("content", [])
            if content_list and isinstance(content_list, list):
                return content_list[0].get("value")
        if entry.get("content:encoded"):
            return entry.get("content:encoded")
        return entry.get("summary")

    def parse(self, raw: bytes | str, source: SourceConfig) -> list[NewsItem]:
        # feedparser handles both bytes and str
        parsed = feedparser.parse(raw)
        items: list[NewsItem] = []

        for entry in parsed.entries:
            published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
            published_at = None
            if published_struct:
                try:
                    dt = datetime.fromtimestamp(mktime(published_struct), tz=timezone.utc)
                    published_at = int(dt.timestamp())
                except Exception:
                    pass  # Fallback to None if date parsing fails

            link = entry.get("link", "")
            if not link:
                continue  # Skip entries without a URL (cannot deduplicate later)

            raw_content = self._extract_content(entry)
            clean_content = self._clean_html(raw_content)

            items.append(
                NewsItem(
                    source_id=source.id,
                    url=link,
                    title=self._clean_html(entry.get("title")),
                    summary=self._clean_html(entry.get("summary")),
                    content=clean_content,
                    author=entry.get("author"),
                    published_at=published_at,
                    language=source.language,
                    tags=source.tags,
                    fetched_at=int(datetime.now(timezone.utc).timestamp()),
                )
            )

        return items
