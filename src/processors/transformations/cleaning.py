"""HTML stripping and normalization (NewsItemStep)."""
from __future__ import annotations

import logging
import re
import unicodedata

from bs4 import BeautifulSoup

from src.common.logging import get_logger
from src.processors.base import NewsItemStep
from src.schemas.models import NewsItem

log = logging.getLogger(__name__)


class NormalizeStep(NewsItemStep):
    def process(self, item: NewsItem) -> NewsItem | None:
        logger = get_logger(__name__)
        try:
            title = _clean_text(item.title)
            summary = _clean_text(item.summary)
            content = _clean_text(item.content)
            author = _clean_text(item.author)

            if not any([title, summary, content]):
                logger.debug("normalize_no_text", url=item.url)
                return None

            result = NewsItem(
                source_id=item.source_id,
                url=item.url.strip(),
                title=title,
                summary=summary,
                content=content,
                author=author,
                published_at=item.published_at,
                language=item.language,
                tags=list({t.lower() for t in item.tags}),
                fetched_at=item.fetched_at,
            )
            logger.debug(
                "normalize_success",
                url=item.url,
                has_title=title is not None,
                has_summary=summary is not None,
                has_content=content is not None,
            )
            return result
        except Exception:
            logger.error("normalize_failed", url=item.url, exc_info=True)
            return None


def _clean_text(text: str | None) -> str | None:
    if not text:
        return None
    try:
        cleaned = BeautifulSoup(text, "lxml").get_text(" ", strip=True)
        cleaned = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", cleaned)).strip()
        return cleaned or None
    except Exception:
        return text
