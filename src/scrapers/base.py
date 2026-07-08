"""Abstract base for news sources (SRP, OCP, DIP)."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from src.schemas.models import NewsItem


@dataclass(frozen=True)
class SourceConfig:
    id: str
    type: str
    url: str
    schedule_cron: str
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class NewsSource(abc.ABC):
    """Interface for all news sources (DIP)."""

    def __init__(self, config: SourceConfig) -> None:
        self.config = config

    @abc.abstractmethod
    async def fetch(self) -> list[NewsItem]:
        """Fetch raw news items from the source."""

    @property
    def source_id(self) -> str:
        return self.config.id


class ParsingStrategy(abc.ABC):
    """Strategy pattern: pluggable parsing for different formats."""

    @abc.abstractmethod
    def parse(self, raw: bytes | str, source: SourceConfig) -> list[NewsItem]:
        ...


class SourceAdapter(abc.ABC):
    """Adapter pattern: convert external payload to internal model."""

    @abc.abstractmethod
    def adapt(self, payload: dict[str, Any], source: SourceConfig) -> NewsItem:
        ...
