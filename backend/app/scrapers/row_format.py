"""
Schema-aligned row format for scraped market signals.

Matches 001_init_schema.sql:
- engagement: reddit_upvotes, reddit_comments, poly_volume, poly_comments,
  twitter_likes, twitter_views, twitter_comments, twitter_reposts
- content_table: source_id (resolved from source name), title, body, url,
  published_at, image_url, latitude, longitude, engagement_id, event_type,
  sentiment_score, market_signal
"""

from __future__ import annotations

from typing import Any

# Engagement keys matching engagement table (all numeric; nulls allowed for twitter_*)
ENGAGEMENT_KEYS = (
    "reddit_upvotes",
    "reddit_comments",
    "poly_volume",
    "poly_comments",
    "twitter_likes",
    "twitter_views",
    "twitter_comments",
    "twitter_reposts",
)


def make_engagement(
    poly_volume: float = 0.0,
    poly_comments: int | None = None,
    reddit_upvotes: int = 0,
    reddit_comments: int = 0,
    twitter_likes: int | None = None,
    twitter_views: int | None = None,
    twitter_comments: int | None = None,
    twitter_reposts: int | None = None,
) -> dict[str, Any]:
    """Build engagement dict for DB insert (matches engagement table columns)."""
    return {
        "reddit_upvotes": reddit_upvotes,
        "reddit_comments": reddit_comments,
        "poly_volume": float(poly_volume),
        "poly_comments": poly_comments if poly_comments is not None else 0,
        "twitter_likes": twitter_likes,
        "twitter_views": twitter_views,
        "twitter_comments": twitter_comments,
        "twitter_reposts": twitter_reposts,
    }


def make_content_row(
    *,
    source: str,
    title: str,
    body: str,
    url: str,
    published_at: Any = None,
    image_url: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    event_type: str | None = None,
    sentiment_score: float | None = None,
    market_signal: float | None = None,
    engagement: dict[str, Any],
) -> dict[str, Any]:
    """Build full scraper row for DB: engagement + content_table fields + source name."""
    return {
        "source": source,
        "title": title or "",
        "body": body or "",
        "url": url,
        "published_at": published_at,
        "image_url": image_url,
        "latitude": latitude,
        "longitude": longitude,
        "event_type": event_type,
        "sentiment_score": sentiment_score,
        "market_signal": market_signal,
        "engagement": {**make_engagement(), **engagement},
    }
