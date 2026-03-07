"""
Scraping service: runs Polymarket and Kalshi scrapers (backend/app/scrapers)
and returns normalized market-signal rows for the FastAPI market-signals endpoint.

Rows are schema-aligned with 001_init_schema.sql (engagement + content_table).
To persist to the database, call persist_market_signals_to_db() after fetch, or
use fetch_and_persist_market_signals() when DATABASE_URL is set.
"""
from __future__ import annotations

import os
from typing import Any

from ..scrapers import kalshi, polymarket


def fetch_all_market_signals(*, verbose: bool = False) -> list[dict[str, Any]]:
    """
    Run Polymarket and Kalshi scrapers and return a combined list of
    normalized market signals. Each item has: title, body, url, published_at,
    engagement (full schema: poly_volume, poly_comments, reddit_*, twitter_*),
    source ("polymarket" | "kalshi"), and optional image_url, event_type, etc.
    """
    combined: list[dict[str, Any]] = []
    try:
        if verbose:
            print("  [Polymarket] fetching...")
        rows = polymarket.fetch_all_rows(max_per_tag=50)
        for r in rows:
            r["source"] = "polymarket"
            combined.append(r)
        if verbose:
            print(f"  [Polymarket] got {len(rows)} rows")
    except Exception as e:
        if verbose:
            print(f"  [Polymarket] failed: {e}")
        combined.append({
            "title": "[Polymarket fetch failed]",
            "body": str(e),
            "url": "",
            "published_at": None,
            "engagement": {"poly_volume": 0.0, "poly_comments": None},
            "source": "polymarket",
            "error": True,
        })
    try:
        if verbose:
            print("  [Kalshi] fetching...")
        rows = kalshi.fetch_all_rows()
        for r in rows:
            r["source"] = "kalshi"
            combined.append(r)
        if verbose:
            print(f"  [Kalshi] got {len(rows)} rows")
    except Exception as e:
        if verbose:
            print(f"  [Kalshi] failed: {e}")
        combined.append({
            "title": "[Kalshi fetch failed]",
            "body": str(e),
            "url": "",
            "published_at": None,
            "engagement": {"poly_volume": 0.0, "poly_comments": None},
            "source": "kalshi",
            "error": True,
        })
    return combined


def persist_market_signals_to_db(rows: list[dict[str, Any]], *, verbose: bool = False) -> tuple[int, int] | None:
    """
    Write scraped rows to the database (engagement + content_table).
    Requires DATABASE_URL. Returns (num_engagement_inserted, num_content_upserted)
    or None if DATABASE_URL is not set or psycopg2 is unavailable.
    """
    if not os.environ.get("DATABASE_URL"):
        if verbose:
            print("  [DB] skip: DATABASE_URL not set")
        return None
    try:
        if verbose:
            print("  [DB] persisting to PostgreSQL...")
        from ..repositories.content_repository import persist_market_signal_rows
        out = persist_market_signal_rows(rows)
        if verbose:
            print(f"  [DB] done: {out[0]} engagement, {out[1]} content rows")
        return out
    except Exception as e:
        if verbose:
            print(f"  [DB] failed: {e}")
        return None


def fetch_and_persist_market_signals(*, verbose: bool = False) -> tuple[list[dict[str, Any]], tuple[int, int] | None]:
    """
    Fetch from Polymarket and Kalshi, then persist to DB if DATABASE_URL is set.
    Returns (rows, persist_result) where persist_result is (eng_count, content_count) or None.
    """
    rows = fetch_all_market_signals(verbose=verbose)
    result = persist_market_signals_to_db(rows, verbose=verbose)
    return rows, result
