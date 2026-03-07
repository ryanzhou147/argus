import json
import math
import os
from typing import Optional

from fastapi import APIRouter, Query

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


def _parse_embedding(emb) -> Optional[list]:
    """Parse a pgvector embedding (string or list) into a Python list of floats."""
    if emb is None:
        return None
    if isinstance(emb, list):
        return emb
    try:
        # pgvector returns strings like "[0.1,0.2,...]"
        return json.loads(str(emb))
    except Exception:
        return None


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


@router.get("/points")
def get_content_points():
    """Return content_table rows with location data from the last 31 days."""
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
                  AND published_at >= NOW() - INTERVAL '31 days'
                ORDER BY published_at DESC
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


@router.get("/arcs")
def get_content_arcs(threshold: float = Query(default=0.7, ge=0.0, le=1.0)):
    """
    Return pairs of content points whose embeddings have cosine similarity >= threshold.
    Falls back to an empty list if DATABASE_URL is not set or embeddings are unavailable.
    """
    try:
        conn = _get_connection()
    except Exception:
        return {"arcs": []}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id::text,
                    latitude,
                    longitude,
                    event_type,
                    embedding::text
                FROM content_table
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND embedding IS NOT NULL
                  AND published_at >= NOW() - INTERVAL '31 days'
                ORDER BY published_at DESC
                LIMIT 200
                """
            )
            rows = cur.fetchall()

        # Parse embeddings; drop rows where parsing fails
        points = []
        for r in rows:
            vec = _parse_embedding(r["embedding"])
            if vec is None:
                continue
            points.append({
                "id": r["id"],
                "lat": r["latitude"],
                "lng": r["longitude"],
                "event_type": r["event_type"],
                "vec": vec,
            })

        arcs = []
        seen = set()
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                key = (points[i]["id"], points[j]["id"])
                if key in seen:
                    continue
                seen.add(key)
                sim = _cosine_similarity(points[i]["vec"], points[j]["vec"])
                if sim >= threshold:
                    arcs.append({
                        "event_a_id": points[i]["id"],
                        "event_b_id": points[j]["id"],
                        "similarity": round(sim, 4),
                        "start_lat": points[i]["lat"],
                        "start_lng": points[i]["lng"],
                        "end_lat": points[j]["lat"],
                        "end_lng": points[j]["lng"],
                        "event_type_a": points[i]["event_type"],
                    })

        return {"arcs": arcs}
    finally:
        conn.close()
