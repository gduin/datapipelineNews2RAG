"""Domain-specific exception hierarchy."""
from __future__ import annotations


class PipelineError(Exception):
    """Base error for the pipeline."""


class ScrapingError(PipelineError):
    pass


class ParsingError(PipelineError):
    pass


class EmbeddingError(PipelineError):
    pass


class VectorStoreError(PipelineError):
    pass


class SchemaError(PipelineError):
    pass
