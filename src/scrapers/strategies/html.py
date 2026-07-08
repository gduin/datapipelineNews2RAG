"""HTML scraping strategy using readability heuristics."""
from __future__ import annotations

from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.scrapers.base import ParsingStrategy, SourceConfig
from src.schemas.models import NewsItem


class HTMLParsingStrategy(ParsingStrategy):
    def parse(self, raw: bytes | str, source: SourceConfig) -> list[NewsItem]:
        soup = BeautifulSoup(raw, "lxml")
        title = soup.find("title")
        article = soup.find("article") or soup
        text = " ".join(p.get_text(" ", strip=True) for p in article.find_all("p"))
        return [
            NewsItem(
                source_id=source.id,
                url=source.url,
                title=title.get_text(strip=True) if title else None,
                summary=None,
                content=text or None,
                author=None,
                published_at=None,
                language=source.language,
                tags=source.tags,
                fetched_at=int(datetime.now(timezone.utc).timestamp()),
            )
        ]
