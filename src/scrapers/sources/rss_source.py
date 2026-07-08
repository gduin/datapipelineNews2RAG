"""Concrete RSS source using async httpx and RSS strategy."""
from __future__ import annotations

import httpx

from src.common.decorators import resilient
from src.common.logging import get_logger
from src.scrapers.base import NewsSource, ParsingStrategy
from src.scrapers.strategies.rss import RSSParsingStrategy
from src.schemas.models import NewsItem

logger = get_logger(__name__)


class RSSSource(NewsSource):
    def __init__(self, config, strategy: ParsingStrategy | None = None) -> None:
        super().__init__(config)
        self._strategy = strategy or RSSParsingStrategy()
        self._client = httpx.AsyncClient(
            timeout=config.extra.get("timeout", 30),
            headers={"User-Agent": config.extra.get("user_agent", "NewsRAGBot/1.0")},
        )

    @resilient(stop_after=3, max_wait=30)
    async def fetch(self) -> list[NewsItem]:
        logger.info("fetching_rss", source=self.source_id, url=self.config.url)
        resp = await self._client.get(self.config.url)
        resp.raise_for_status()
        return self._strategy.parse(resp.content, self.config)

    async def close(self) -> None:
        await self._client.aclose()
