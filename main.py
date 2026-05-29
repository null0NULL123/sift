#!/usr/bin/env python3
"""Tech Pulse - Weekly tech blog digest with AI summarization."""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("tech-pulse")


def main():
    load_dotenv()

    # Validate required env vars
    required = ["API_BASE_URL", "API_KEY", "SMTP_SENDER", "SMTP_AUTH_CODE", "SMTP_RECEIVER"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        log.error(f"Missing env vars: {', '.join(missing)}")
        log.error("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    days = int(os.environ.get("SUMMARY_DAYS", "7"))
    language = os.environ.get("SUMMARY_LANGUAGE", "zh-CN")

    # Step 0: Initialize knowledge base
    from knowledge import init_db, save_articles, save_digest, generate_trend_context
    log.info("Initializing knowledge base...")
    init_db()

    # Step 1: Fetch RSS feeds
    from fetcher import fetch_all
    log.info(f"Fetching RSS feeds (last {days} days)...")
    results = fetch_all("feeds.json", days=days)

    total_entries = sum(len(r["entries"]) for r in results)
    errors = [r["name"] for r in results if r["error"]]
    log.info(f"Fetched {total_entries} articles from {len(results)} sources")
    if errors:
        log.warning(f"Failed sources: {', '.join(errors)}")

    # Step 2: Save articles to knowledge base
    new_count = save_articles(results)
    log.info(f"Saved {new_count} new articles to knowledge base")

    # Step 3: Generate summary with trend context
    from summarizer import summarize
    trend_context = generate_trend_context()
    if trend_context:
        log.info("Injecting historical trend context into summary")
    log.info("Generating AI summary...")
    summary = summarize(results, language=language, trend_context=trend_context)
    log.info(f"Summary generated ({len(summary)} chars)")

    # Step 4: Save digest to knowledge base
    save_digest(summary, total_entries)
    log.info("Digest saved to knowledge base")

    # Step 5: Save to file
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    filename = f"tech-pulse-{datetime.now().strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename
    output_path.write_text(summary, encoding="utf-8")
    log.info(f"Saved to {output_path}")

    # Step 6: Send email
    from mailer import send
    if not send(summary):
        sys.exit(1)

    log.info("Done!")


if __name__ == "__main__":
    main()
