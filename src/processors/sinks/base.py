"""Vector sink abstraction (Repository pattern, DIP)."""
from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict


class VectorSink(abc.ABC):
    @abc.abstractmethod
    def upsert(self, records: list[VectorRecord]) -> int:
        ...

    @abc.abstractmethod
    def ensure_collection(self, vector_size: int) -> None:
        ...
