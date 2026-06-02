"""Test base utilities - reusable fixtures and helpers."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sift.models import Entry, FeedResult, SourceConfig
from sift.storage.knowledge import KnowledgeStorage


# ------------------------------------------------------------------
# Context managers
# ------------------------------------------------------------------

@contextmanager
def temp_db():
    """Context manager providing a temporary KnowledgeStorage instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["DB_PATH"] = os.path.join(tmpdir, "test.db")
        try:
            ks = KnowledgeStorage()
            ks.initialize()
            yield ks
            ks.close()
        finally:
            os.environ.pop("DB_PATH", None)


@contextmanager
def temp_dir():
    """Context manager for a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@contextmanager
def env_vars(**kwargs):
    """Context manager to set and restore environment variables."""
    saved = {k: os.environ.get(k) for k in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextmanager
def temp_file(content: str, suffix: str = ".tmp"):
    """Context manager for a temporary file with content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        yield tmp_path
    finally:
        os.unlink(tmp_path)


@contextmanager
def temp_json(data):
    """Context manager for a temporary JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name
    try:
        yield tmp_path
    finally:
        os.unlink(tmp_path)


# ------------------------------------------------------------------
# Model factories
# ------------------------------------------------------------------

def make_entry(title: str, link: str = None, summary: str = "") -> Entry:
    """Create a test Entry with defaults."""
    return Entry(
        title=title,
        link=link or f"http://test/{title.lower().replace(' ', '-')}",
        published=datetime.now(timezone.utc),
        summary=summary,
    )


def make_feed(entries: list[Entry], source_name: str = "Test") -> FeedResult:
    """Create a FeedResult from entries."""
    cfg = SourceConfig(name=source_name, url="http://test")
    return FeedResult(config=cfg, entries=entries)


def make_source(name: str = "Test", url: str = "http://test", **kwargs) -> SourceConfig:
    """Create a test SourceConfig with defaults."""
    return SourceConfig(name=name, url=url, **kwargs)
