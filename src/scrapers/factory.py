"""Abstract Factory + registry (OCP: add new sources without modification)."""
from __future__ import annotations

from typing import ClassVar

from src.common.exceptions import ScrapingError
from src.scrapers.base import NewsSource, SourceConfig
from src.scrapers.sources.rss_source import RSSSource


class NewsSourceFactory:
    _registry: ClassVar[dict[str, type[NewsSource]]] = {}

    @classmethod
    def register(cls, source_type: str) -> type:
        def decorator(klass: type[NewsSource]) -> type[NewsSource]:
            cls._registry[source_type] = klass
            return klass
        return decorator

    @classmethod
    def create(cls, config: SourceConfig) -> NewsSource:
        try:
            klass = cls._registry[config.type]
        except KeyError as exc:
            raise ScrapingError(f"Unknown source type: {config.type}") from exc
        return klass(config)


NewsSourceFactory.register("rss")(RSSSource)
