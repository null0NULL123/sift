"""Knowledge accumulation module - stores articles, tracks trends, enables semantic search.

Uses SQLite + sqlite-vec for structured + vector queries in a single .db file.
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlite_vec

DB_PATH = "knowledge/pulse.db"
EMBEDDING_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2


def _get_db() -> sqlite3.Connection:
    """Get database connection with sqlite-vec loaded."""
    Path("knowledge").mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init_db():
    """Initialize database schema and vector table."""
    db = _get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            source TEXT NOT NULL,
            published TEXT,
            summary TEXT,
            tags TEXT DEFAULT '[]',
            week TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week TEXT NOT NULL,
            topic TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            UNIQUE(week, topic)
        );

        CREATE TABLE IF NOT EXISTS digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            article_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_articles_week ON articles(week);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published);
        CREATE INDEX IF NOT EXISTS idx_topics_week ON topics(week);
    """)

    # Create vector virtual table for semantic search
    db.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS article_vec USING vec0(
            article_id INTEGER PRIMARY KEY,
            embedding float[{EMBEDDING_DIM}]
        )
    """)
    db.commit()
    db.close()


def _article_hash(title: str, link: str) -> str:
    """Generate unique hash for deduplication."""
    return hashlib.sha256(f"{title}|{link}".encode()).hexdigest()[:16]


def _get_week_id(dt: datetime = None) -> str:
    """Get ISO week identifier like '2026-W22'."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _get_embedding(text: str) -> list[float] | None:
    """Generate embedding vector for text. Uses API if available, else None."""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["API_KEY"],
            base_url=os.environ["API_BASE_URL"],
        )
        model = os.environ.get("EMBEDDING_MODEL", "")
        if not model:
            return None
        response = client.embeddings.create(model=model, input=text[:2000])
        return response.data[0].embedding
    except Exception:
        return None


def save_articles(feed_results: list[dict]) -> int:
    """Save fetched articles to database. Returns count of new articles."""
    db = _get_db()
    week = _get_week_id()
    saved = 0

    for feed in feed_results:
        if feed["error"]:
            continue
        for entry in feed["entries"]:
            h = _article_hash(entry["title"], entry["link"])
            try:
                db.execute(
                    """INSERT OR IGNORE INTO articles (hash, title, link, source, published, summary, week)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (h, entry["title"], entry["link"], feed["name"],
                     entry.get("published", ""), entry.get("summary", ""), week)
                )
                if db.execute("SELECT changes()").fetchone()[0] > 0:
                    saved += 1

                    # Generate and store embedding
                    embed_text = f"{entry['title']} {entry.get('summary', '')}"
                    embedding = _get_embedding(embed_text)
                    if embedding:
                        article_id = db.execute(
                            "SELECT id FROM articles WHERE hash = ?", (h,)
                        ).fetchone()[0]
                        db.execute(
                            "INSERT OR REPLACE INTO article_vec (article_id, embedding) VALUES (?, vec_f32(?))",
                            (article_id, json.dumps(embedding))
                        )
            except sqlite3.IntegrityError:
                pass

    db.commit()
    db.close()
    return saved


def save_topics(topics: list[str], week: str = None):
    """Save or increment topic counts for a given week."""
    db = _get_db()
    week = week or _get_week_id()
    for topic in topics:
        topic = topic.strip().lower()
        if not topic:
            continue
        db.execute(
            """INSERT INTO topics (week, topic, count) VALUES (?, ?, 1)
               ON CONFLICT(week, topic) DO UPDATE SET count = count + 1""",
            (week, topic)
        )
    db.commit()
    db.close()


def save_digest(content: str, article_count: int, week: str = None):
    """Save weekly digest content."""
    db = _get_db()
    week = week or _get_week_id()
    db.execute(
        """INSERT OR REPLACE INTO digests (week, content, article_count) VALUES (?, ?, ?)""",
        (week, content, article_count)
    )
    db.commit()
    db.close()


def get_articles(weeks: int = 4, source: str = None) -> list[dict]:
    """Get articles from the last N weeks."""
    db = _get_db()
    db.row_factory = sqlite3.Row
    cutoff_week = _get_week_id(datetime.now(timezone.utc) - timedelta(weeks=weeks))

    if source:
        rows = db.execute(
            "SELECT * FROM articles WHERE week >= ? AND source = ? ORDER BY published DESC",
            (cutoff_week, source)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM articles WHERE week >= ? ORDER BY published DESC",
            (cutoff_week,)
        ).fetchall()

    db.close()
    return [dict(r) for r in rows]


def search_similar(query: str, limit: int = 5) -> list[dict]:
    """Semantic search: find articles most similar to query text."""
    embedding = _get_embedding(query)
    if not embedding:
        return []

    db = _get_db()
    db.row_factory = sqlite3.Row
    rows = db.execute("""
        SELECT a.*, v.distance
        FROM article_vec v
        JOIN articles a ON a.id = v.article_id
        WHERE v.embedding MATCH vec_f32(?)
        ORDER BY v.distance ASC
        LIMIT ?
    """, (json.dumps(embedding), limit)).fetchall()

    db.close()
    return [dict(r) for r in rows]


def get_topic_trends(months: int = 3) -> list[dict]:
    """Get topic frequency trends over the last N months."""
    db = _get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    # Approximate week cutoff
    cutoff_week = _get_week_id(cutoff)

    rows = db.execute("""
        SELECT topic, week, count
        FROM topics
        WHERE week >= ?
        ORDER BY week ASC, count DESC
    """, (cutoff_week,)).fetchall()
    db.close()

    # Organize by topic
    trends = {}
    for topic, week, count in rows:
        if topic not in trends:
            trends[topic] = {"topic": topic, "weeks": [], "total": 0}
        trends[topic]["weeks"].append({"week": week, "count": count})
        trends[topic]["total"] += count

    # Sort by total frequency
    return sorted(trends.values(), key=lambda x: x["total"], reverse=True)


def get_rising_topics(weeks: int = 4) -> list[dict]:
    """Detect topics with rising frequency in recent weeks."""
    trends = get_topic_trends(months=2)
    rising = []

    for t in trends:
        if len(t["weeks"]) < 2:
            continue
        recent = t["weeks"][-1]["count"]
        previous = sum(w["count"] for w in t["weeks"][:-1]) / max(len(t["weeks"]) - 1, 1)
        if recent > previous * 1.5 and recent >= 2:
            rising.append({
                "topic": t["topic"],
                "recent_count": recent,
                "avg_previous": round(previous, 1),
                "trend": "rising"
            })

    return rising


def generate_trend_context() -> str:
    """Generate trend analysis text to inject into next digest prompt."""
    trends = get_topic_trends(months=3)
    rising = get_rising_topics()

    if not trends and not rising:
        return ""

    lines = ["## 历史趋势参考（供摘要参考，不输出到周报中）\n"]

    if rising:
        lines.append("### 上升趋势话题")
        for r in rising[:5]:
            lines.append(f"- {r['topic']}: 近期 {r['recent_count']} 次，此前平均 {r['avg_previous']} 次")

    if trends:
        lines.append("\n### 近 3 个月高频话题")
        for t in trends[:10]:
            weeks_str = ", ".join(f"{w['week']}({w['count']})" for w in t["weeks"][-4:])
            lines.append(f"- {t['topic']}: 总计 {t['total']} 次 | 近期: {weeks_str}")

    return "\n".join(lines)
