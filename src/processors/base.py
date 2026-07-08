"""Chain of Responsibility: each step transforms NewsItem(s)."""
from __future__ import annotations

import abc
from typing import Generic, TypeVar

from src.schemas.models import NewsChunk, NewsItem

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class TransformationStep(abc.ABC, Generic[TIn, TOut]):
    """Single transformation in the pipeline."""

    @abc.abstractmethod
    def process(self, item: TIn) -> TOut | None:
        """Return transformed item or None to drop."""


class NewsItemStep(TransformationStep[NewsItem, NewsItem]):
    pass


class ChunkStep(TransformationStep[NewsItem, list[NewsChunk]]):
    pass
