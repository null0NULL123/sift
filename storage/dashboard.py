"""Dashboard queries - stats, digests, source distribution, and preferences."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from models import Digest

from .base import BaseStorage


class DashboardStorage(BaseStorage):
    """Dashboard statistics, digest queries, and user preferences."""

    # ------------------------------------------------------------------
    # Preferences (key-value store)
    # ------------------------------------------------------------------

    def get_preference(self, key: str, default: str = "") -> str:
        db = self._get_db()
        row = db.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_preference(self, key: str, value: str) -> None:
        db = self._get_db()
        db.execute(
            "INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, datetime('now')) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value),
        )
        db.commit()

    def get_all_preferences(self) -> dict[str, str]:
        db = self._get_db()
        rows = db.execute("SELECT key, value FROM preferences").fetchall()
        return {r[0]: r[1] for r in rows}

    # ------------------------------------------------------------------
    # Digest operations
    # ------------------------------------------------------------------

    def save_digest(self, digest: Digest) -> None:
        db = self._get_db()
        week = digest.week or self._week_id()
        db.execute(
            "INSERT OR REPLACE INTO digests (week, content, article_count) VALUES (?, ?, ?)",
            (week, digest.content, digest.article_count),
        )
        db.commit()

    def get_digests(self, limit: int = 10) -> list[dict]:
        db = self._get_db()
        rows = db.execute(
            "SELECT week, content, article_count, created_at FROM digests ORDER BY week DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"week": r[0], "content": r[1], "article_count": r[2], "created_at": r[3]} for r in rows]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        db = self._get_db()
        article_count = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        source_count = db.execute("SELECT COUNT(DISTINCT source) FROM articles").fetchone()[0]
        digest_count = db.execute("SELECT COUNT(*) FROM digests").fetchone()[0]
        week_count = db.execute("SELECT COUNT(DISTINCT week) FROM articles").fetchone()[0]
        return {
            "articles": article_count,
            "sources": source_count,
            "digests": digest_count,
            "weeks": week_count,
        }

    def get_source_distribution(self, weeks: int = 12) -> list[dict]:
        db = self._get_db()
        cutoff = self._week_id(datetime.now(timezone.utc) - timedelta(weeks=weeks))
        rows = db.execute(
            "SELECT source, COUNT(*) as cnt FROM articles WHERE week >= ? GROUP BY source ORDER BY cnt DESC",
            (cutoff,),
        ).fetchall()
        return [{"source": r[0], "count": r[1]} for r in rows]
