"""HTML stripping and normalization (NewsItemStep)."""
from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from src.processors.base import NewsItemStep
from src.schemas.models import NewsItem

_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


class NormalizeStep(NewsItemStep):
    def process(self, item: NewsItem) -> NewsItem | None:
        def _clean(text: str | None) -> str | None:
            if not text:
                return None
            text = BeautifulSoup(text, "lxml").get_text(" ", strip=True)
            text = _WS.sub(" ", unicodedata.normalize("NFKC", text)).strip()
            return text or None

        return NewsItem(
            source_id=item.source_id,
            url=item.url.strip(),
            title=_clean(item.title),
            summary=_clean(item.summary),
            content=_clean(item.content),
            author=_clean(item.author),
            published_at=item.published_at,
            language=item.language,
            tags=list({t.lower() for t in item.tags}),
            fetched_at=item.fetched_at,
        )
