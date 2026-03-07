import os
from typing import Optional

from fastapi import APIRouter

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

router = APIRouter(prefix="/content", tags=["content"])


def _get_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(url)


@router.get("/points")
def get_content_points():
    """Return all content_table rows that have latitude and longitude set."""
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id::text,
                    title,
                    latitude,
                    longitude,
                    event_type,
                    published_at
                FROM content_table
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                ORDER BY published_at DESC NULLS LAST
                """
            )
            rows = cur.fetchall()
        points = []
        for r in rows:
            points.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "event_type": r["event_type"],
                    "published_at": r["published_at"].isoformat() if r["published_at"] else None,
                }
            )
        return {"points": points}
    finally:
        conn.close()
