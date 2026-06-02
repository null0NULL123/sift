"""Sources tests."""

from __future__ import annotations

from datetime import timezone

from sift.sources.rss import RSSSource
from sift.sources.web import _DEFAULTS


def test_rss_parse_date():
    class FakeEntry:
        published_parsed = (2026, 5, 30, 12, 0, 0, 0, 0, 0)

    dt = RSSSource._parse_date(FakeEntry())
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 30
    assert dt.tzinfo == timezone.utc


def test_web_defaults():
    assert "selector" in _DEFAULTS
    assert "title_sel" in _DEFAULTS
    assert _DEFAULTS["selector"] == "article"


TESTS = [
    ("RSS parse_date", test_rss_parse_date),
    ("Web defaults", test_web_defaults),
]
