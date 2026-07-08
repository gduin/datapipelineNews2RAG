import pytest

from src.common.exceptions import ScrapingError
from src.scrapers.base import SourceConfig
from src.scrapers.factory import NewsSourceFactory
from src.scrapers.sources.rss_source import RSSSource


def test_factory_creates_rss():
    cfg = SourceConfig(id="t", type="rss", url="http://x.test/feed",
                       schedule_cron="*/5 * * * *")
    src = NewsSourceFactory.create(cfg)
    assert isinstance(src, RSSSource)


def test_factory_unknown_type_raises():
    cfg = SourceConfig(id="t", type="nonexistent", url="http://x.test",
                       schedule_cron="*/5 * * * *")
    with pytest.raises(ScrapingError):
        NewsSourceFactory.create(cfg)
