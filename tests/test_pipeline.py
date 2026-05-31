"""Pipeline tests."""

from __future__ import annotations

from base import make_source
from config import DEFAULT_DAYS, DEFAULT_LANGUAGE
from pipeline import Pipeline, create_source


def test_create_source():
    rss = create_source(make_source())
    assert type(rss).__name__ == "RSSSource"

    web = create_source(make_source(url="http://x", source_type="web"))
    assert type(web).__name__ == "WebSource"

    try:
        create_source(make_source(source_type="unknown"))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_pipeline_init():
    p = Pipeline(sources=[], storage=None)
    assert p.days == DEFAULT_DAYS
    assert p.language == DEFAULT_LANGUAGE
    assert p.channels == []

    p2 = Pipeline(sources=[], storage=None, days=3, language="en")
    assert p2.days == 3
    assert p2.language == "en"


TESTS = [
    ("create_source", test_create_source),
    ("Pipeline init", test_pipeline_init),
]
