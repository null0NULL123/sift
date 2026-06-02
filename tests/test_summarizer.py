"""Summarizer tests."""

from __future__ import annotations

from base import make_entry, make_feed, make_source
from sift.config import LOCALE
from sift.models import FeedResult
from sift.processors.summarizer import SummarizeProcessor, _prompts_dir, load_prompt


def test_prompt_loading():
    assert _prompts_dir().exists()
    prompt = load_prompt("tech-weekly")
    assert len(prompt) > 0
    assert isinstance(prompt, str)


def test_build_prompt():
    class FakeProcessor:
        _build_user_prompt = SummarizeProcessor._build_user_prompt

    feed = make_feed([
        make_entry("Test Article", summary="A test summary"),
        make_entry("Another"),
    ], source_name="Blog")
    error_result = FeedResult(config=make_source("Blog"), error="timeout")

    fp = FakeProcessor()
    prompt = fp._build_user_prompt([feed, error_result], "zh-CN")

    assert "Test Article" in prompt
    assert "Another" in prompt
    assert "Blog" in prompt
    assert "timeout" in prompt
    assert "2" in prompt


def test_empty_prompt():
    class FakeProcessor:
        _build_user_prompt = SummarizeProcessor._build_user_prompt

    feed = make_feed([], source_name="Blog")

    fp = FakeProcessor()
    prompt = fp._build_user_prompt([feed], "zh-CN")
    assert LOCALE["no_articles"] in prompt


TESTS = [
    ("prompt loading", test_prompt_loading),
    ("build prompt", test_build_prompt),
    ("empty prompt", test_empty_prompt),
]
