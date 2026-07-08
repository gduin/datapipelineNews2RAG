"""Reusable decorators (Decorator pattern)."""
from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

P = ParamSpec("P")
T = TypeVar("T")


def with_metrics(name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def deco(fn: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                logger.info("metric", name=name, duration_ms=round((time.perf_counter() - start) * 1000, 2))
        return sync_wrapper
    return deco


def resilient(stop_after: int = 3, max_wait: float = 30.0) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Apply tenacity retry with exponential backoff."""
    def deco(fn: Callable[P, T]) -> Callable[P, T]:
        retried = retry(
            stop=stop_after_attempt(stop_after),
            wait=wait_exponential(multiplier=1, max=max_wait),
            reraise=True,
        )
        return retried(fn)
    return deco


async def gather_with_concurrency(n: int, *coros: Coroutine[Any, Any, T]) -> list[T]:
    sem = asyncio.Semaphore(n)

    async def bound(c: Coroutine[Any, Any, T]) -> T:
        async with sem:
            return await c

    return await asyncio.gather(*(bound(c) for c in coros))
