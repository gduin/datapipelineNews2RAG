from src.processors.transformations.cleaning import NormalizeStep
from src.schemas.models import NewsItem


def test_strips_html():
    item = NewsItem(
        source_id="s", url="https://x.test",
        title="<b>Hi</b>", content="<p>Hello &amp; <i>world</i></p>",
        tags=["News", "news"], fetched_at=1,
    )
    out = NormalizeStep().process(item)
    assert out is not None
    assert out.title == "Hi"
    assert out.content == "Hello & world"
    assert out.tags == ["news"]


def test_item_with_empty_text_returns_none():
    item = NewsItem(source_id="s", url="https://x.test", fetched_at=1)
    out = NormalizeStep().process(item)
    assert out is None
