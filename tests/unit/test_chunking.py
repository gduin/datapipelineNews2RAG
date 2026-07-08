from src.processors.transformations.chunking import SentenceChunker
from src.schemas.models import NewsItem


def make_item(content: str) -> NewsItem:
    return NewsItem(
        source_id="t", url="https://x.test/a",
        content=content, fetched_at=1,
    )


def test_chunker_single_chunk_for_short_text():
    chunker = SentenceChunker(max_tokens=512, overlap_tokens=64)
    item = make_item("Hello world. This is a test sentence.")
    chunks = chunker.process(item)
    assert chunks and len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks == 1
    assert chunks[0].chunk_id  # sha1 hex


def test_chunker_splits_long_text():
    paragraph = "This is a sentence. " * 200  # ~800 tokens
    item = make_item(paragraph)
    chunker = SentenceChunker(max_tokens=64, overlap_tokens=16)
    chunks = chunker.process(item)
    assert len(chunks) > 1
    assert all(c.url == item.url for c in chunks)
    assert {c.chunk_index for c in chunks} == set(range(len(chunks)))


def test_chunker_returns_none_for_empty():
    chunker = SentenceChunker()
    assert chunker.process(NewsItem(source_id="t", url="u")) is None
