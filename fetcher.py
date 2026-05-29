"""RSS feed fetcher - pulls and filters posts from the last N days."""

import json
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser


def _parse_date(entry) -> datetime | None:
    """Extract published date from a feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _fetch_one(feed_cfg: dict, since: datetime) -> dict:
    """Fetch a single RSS feed and filter entries newer than `since`."""
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    try:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            return {"name": name, "url": url, "entries": [], "error": str(parsed.bozo_exception)}

        entries = []
        for entry in parsed.entries:
            pub_date = _parse_date(entry)
            if pub_date and pub_date < since:
                continue
            entries.append({
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "published": pub_date.isoformat() if pub_date else "",
                "summary": entry.get("summary", "")[:500],
            })
        return {"name": name, "url": url, "entries": entries, "error": None}
    except Exception as e:
        return {"name": name, "url": url, "entries": [], "error": str(e)}


def fetch_all(feeds_path: str = "feeds.json", days: int = 7) -> list[dict]:
    """Fetch all feeds in parallel, return entries from the last N days."""
    with open(feeds_path, "r", encoding="utf-8") as f:
        feeds = json.load(f)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    results = []

    with ThreadPoolExecutor(max_workers=min(len(feeds), 8)) as pool:
        futures = {pool.submit(_fetch_one, feed, since): feed for feed in feeds}
        for future in as_completed(futures):
            results.append(future.result())

    # Sort by feed order in config
    feed_order = {f["url"]: i for i, f in enumerate(feeds)}
    results.sort(key=lambda r: feed_order.get(r["url"], 99))
    return results
