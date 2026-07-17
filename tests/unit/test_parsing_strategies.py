"""Tests for scraper strategies: RSS parsing, HTML parsing."""

from src.scrapers.base import SourceConfig
from src.scrapers.strategies.rss import RSSParsingStrategy
from src.scrapers.strategies.html import HTMLParsingStrategy


def make_cfg(id="test_src") -> SourceConfig:
    return SourceConfig(
        id=id, type="rss", url="http://example.com/feed",
        schedule_cron="*/5 * * * *",
        tags=["finance"], language="en",
    )


class TestRSSParsingStrategy:
    def test_parse_valid_feed(self):
        raw = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <item>
    <title>Market Update</title>
    <link>https://example.com/article/1</link>
    <description>Daily summary of markets</description>
    <author>Jane Doe</author>
    <pubDate>Mon, 01 Apr 2024 10:00:00 GMT</pubDate>
    <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">
      <![CDATA[<p>Full article text</p>]]>
    </content:encoded>
  </item>
</channel>
</rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert len(items) == 1
        assert items[0].title == "Market Update"
        assert items[0].url == "https://example.com/article/1"
        assert items[0].author == "Jane Doe"
        assert items[0].content == "Full article text"
        assert items[0].source_id == "test_src"
        assert items[0].tags == ["finance"]
        assert items[0].published_at is not None
        assert items[0].language == "en"

    def test_no_entries(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel></channel></rss>"""
        assert RSSParsingStrategy().parse(raw, make_cfg()) == []

    def test_summary_fallback_when_no_content(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>No Content</title><link>https://x.com/2</link>
<description>HTML <b>bold</b> text</description></item>
</channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert len(items) == 1
        assert items[0].content == "HTML bold text"

    def test_content_prefers_full_content_over_summary(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><link>https://x.com/1</link>
<description>Summary text</description>
<content:encoded><![CDATA[Full <p>article</p> body]]></content:encoded>
</item></channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert items[0].content == "Full article body"

    def test_missing_url_is_skipped(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>no url item</title></item>
<item><link>https://x.com/with-url</link></item>
</channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert len(items) == 1
        assert items[0].url == "https://x.com/with-url"

    def test_html_entities_decoded(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><link>https://x.com/3</link>
<description>Items with &amp; and &lt;tags</description></item>
</channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert "items with" in items[0].content.lower()

    def test_dublincore_date_fallback(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><link>https://x.com/dt</link>
<dc:date>2024-01-01T00:00:00Z</dc:date></item>
</channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert items[0].published_at is not None

    def test_missing_date_is_none(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><link>https://x.com/nd</link></item></channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert items[0].published_at is None

    def test_atom_feed(self):
        raw = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry>
    <title>Atom entry</title>
    <id>https://x.com/atom-test</id>
    <content>Hello content</content>
</entry>
</feed>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert len(items) == 1
        assert items[0].title == "Atom entry"

    def test_cdata_content_handled(self):
        raw = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><link>https://x.com/5</link>
<content:encoded><![CDATA[text with special <chars>]]></content:encoded></item>
</channel></rss>"""
        items = RSSParsingStrategy().parse(raw, make_cfg())
        assert "text with special" in items[0].content


class TestHTMLParsingStrategy:
    def test_parse_basic_html(self):
        html = """<html><head><title>Page Title</title></head>
<body><article>
<p>First paragraph.</p>
<p>Second paragraph.</p>
</article></body></html>"""
        items = HTMLParsingStrategy().parse(html, make_cfg())
        assert len(items) == 1
        assert items[0].title == "Page Title"
        assert items[0].content == "First paragraph. Second paragraph."
        assert items[0].url == "http://example.com/feed"
        assert items[0].source_id == "test_src"

    def test_no_article_fallback_to_body(self):
        html = """<html><head><title>T</title></head>
<body><p>Body text only</p></body></html>"""
        items = HTMLParsingStrategy().parse(html, make_cfg())
        assert items[0].content == "Body text only"

    def test_no_title(self):
        html = """<html><body><p>No title here</p></body></html>"""
        items = HTMLParsingStrategy().parse(html, make_cfg())
        assert items[0].title is None

    def test_empty_html(self):
        html = "<html></html>"
        items = HTMLParsingStrategy().parse(html, make_cfg())
        assert items[0].content is None

    def test_rich_html(self):
        html = """<html><head><title>Rich</title></head>
<body>
<h1>Header</h1>
<p>Paragraph <b>bold</b> and <a href="http://x.com">link</a></p>
</body></html>"""
        items = HTMLParsingStrategy().parse(html, make_cfg())
        assert "bold" in items[0].content
        assert "link" in items[0].content