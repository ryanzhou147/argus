"""
Scraping service: runs Polymarket and Kalshi scrapers (backend/app/scrapers)
and returns normalized market-signal rows for the FastAPI market-signals endpoint.
"""
from __future__ import annotations

from typing import Any

from ..scrapers import kalshi, polymarket


def fetch_all_market_signals() -> list[dict[str, Any]]:
    """
    Run Polymarket and Kalshi scrapers and return a combined list of
    normalized market signals. Each item has: title, body, url, published_at,
    engagement (poly_volume, poly_comments), source ("polymarket" | "kalshi").
    """
    combined: list[dict[str, Any]] = []
    try:
        rows = polymarket.fetch_all_rows(max_per_tag=50)
        for r in rows:
            r["source"] = "polymarket"
            combined.append(r)
    except Exception as e:
        combined.append({
            "title": "[Polymarket fetch failed]",
            "body": str(e),
            "url": "",
            "published_at": None,
            "engagement": {"poly_volume": 0, "poly_comments": None},
            "source": "polymarket",
            "error": True,
        })
    try:
        rows = kalshi.fetch_all_rows()
        for r in rows:
            r["source"] = "kalshi"
            combined.append(r)
    except Exception as e:
        combined.append({
            "title": "[Kalshi fetch failed]",
            "body": str(e),
            "url": "",
            "published_at": None,
            "engagement": {"poly_volume": 0, "poly_comments": None},
            "source": "kalshi",
            "error": True,
        })
    return combined
