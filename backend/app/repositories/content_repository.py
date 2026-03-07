"""
Persist scraped market-signal rows to the database (engagement + content_table only).

Uses 001_init_schema.sql: engagement, content_table. Does not write to sources.
content_table: only id (default), title, body, url, published_at, image_url, event_type, engagement_id.
Set DATABASE_URL to enable; if unset, persist methods no-op or raise.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

# Optional: only used when DATABASE_URL is set
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

from ..scrapers.row_format import ENGAGEMENT_KEYS, make_engagement


def _get_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed; add psycopg2-binary to requirements.txt")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set; cannot persist to database")
    return psycopg2.connect(url)


@contextmanager
def get_cursor():
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _engagement_row(row: dict[str, Any]) -> dict[str, Any]:
    eng = row.get("engagement") or {}
    out = make_engagement()
    for k in ENGAGEMENT_KEYS:
        if k in eng and eng[k] is not None:
            out[k] = eng[k]
    return out


def persist_market_signal_rows(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """
    Write scraped rows to engagement and content_table only (not sources).
    content_table: only title, body, url, published_at, image_url, event_type, engagement_id.
    Returns (num_engagement_inserted, num_content_upserted). Skips rows with error=True or empty url.
    """
    if not rows:
        return 0, 0
    with get_cursor() as cur:
        num_eng = 0
        num_content = 0
        for row in rows:
            if row.get("error") or not (row.get("url") or "").strip():
                continue
            eng = _engagement_row(row)

            # Upsert by url: if content exists, update its engagement row and content fields
            cur.execute(
                "SELECT id, engagement_id FROM content_table WHERE url = %s",
                (row["url"],),
            )
            existing = cur.fetchone()

            if existing:
                engagement_id = existing["engagement_id"]
                if not engagement_id:
                    cur.execute(
                        """
                        INSERT INTO engagement (
                            reddit_upvotes, reddit_comments, poly_volume, poly_comments,
                            twitter_likes, twitter_views, twitter_comments, twitter_reposts
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            eng["reddit_upvotes"],
                            eng["reddit_comments"],
                            eng["poly_volume"],
                            eng["poly_comments"],
                            eng.get("twitter_likes"),
                            eng.get("twitter_views"),
                            eng.get("twitter_comments"),
                            eng.get("twitter_reposts"),
                        ),
                    )
                    new_eng = cur.fetchone()
                    engagement_id = new_eng["id"] if new_eng else None
                    num_eng += 1
                else:
                    cur.execute(
                        """
                        UPDATE engagement SET
                            reddit_upvotes = %s, reddit_comments = %s,
                            poly_volume = %s, poly_comments = %s,
                            twitter_likes = %s, twitter_views = %s,
                            twitter_comments = %s, twitter_reposts = %s
                        WHERE id = %s
                        """,
                        (
                            eng["reddit_upvotes"],
                            eng["reddit_comments"],
                            eng["poly_volume"],
                            eng["poly_comments"],
                            eng.get("twitter_likes"),
                            eng.get("twitter_views"),
                            eng.get("twitter_comments"),
                            eng.get("twitter_reposts"),
                            engagement_id,
                        ),
                    )
                cur.execute(
                    """
                    UPDATE content_table SET
                        title = %s, body = %s, published_at = %s,
                        image_url = %s, engagement_id = %s, event_type = %s,
                        latitude = %s, longitude = %s
                    WHERE url = %s
                    """,
                    (
                        row.get("title") or "",
                        row.get("body") or "",
                        row.get("published_at"),
                        row.get("image_url"),
                        engagement_id,
                        row.get("event_type"),
                        row.get("latitude"),
                        row.get("longitude"),
                        row["url"],
                    ),
                )
                num_content += 1
            else:
                cur.execute(
                    """
                    INSERT INTO engagement (
                        reddit_upvotes, reddit_comments, poly_volume, poly_comments,
                        twitter_likes, twitter_views, twitter_comments, twitter_reposts
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        eng["reddit_upvotes"],
                        eng["reddit_comments"],
                        eng["poly_volume"],
                        eng["poly_comments"],
                        eng.get("twitter_likes"),
                        eng.get("twitter_views"),
                        eng.get("twitter_comments"),
                        eng.get("twitter_reposts"),
                    ),
                )
                new_eng = cur.fetchone()
                engagement_id = new_eng["id"] if new_eng else None
                num_eng += 1
                cur.execute(
                    """
                    INSERT INTO content_table (
                        title, body, url, published_at, image_url,
                        engagement_id, event_type, latitude, longitude
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO UPDATE SET
                        title = EXCLUDED.title, body = EXCLUDED.body,
                        published_at = EXCLUDED.published_at, image_url = EXCLUDED.image_url,
                        engagement_id = EXCLUDED.engagement_id, event_type = EXCLUDED.event_type,
                        latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
                    """,
                    (
                        row.get("title") or "",
                        row.get("body") or "",
                        row["url"],
                        row.get("published_at"),
                        row.get("image_url"),
                        engagement_id,
                        row.get("event_type"),
                        row.get("latitude"),
                        row.get("longitude"),
                    ),
                )
                num_content += 1
        return num_eng, num_content
