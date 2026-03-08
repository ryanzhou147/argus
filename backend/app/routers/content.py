import json
import math
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.agent_schemas import RealTimeAnalysisRequest, RealTimeAnalysisResponse
from ..services.gemini_client import call_gemini_realtime_analysis

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


@router.post("/{content_id}/realtime-analysis", response_model=RealTimeAnalysisResponse)
def realtime_analysis(content_id: str, request: RealTimeAnalysisRequest) -> RealTimeAnalysisResponse:
    """
    Fetch event title + body and call Gemini with Google Search grounding
    to produce a max-3-sentence persona-aware analysis of recent developments.
    """
    # Fetch title + body from DB (best-effort; fallback to empty strings)
    title = ""
    body = ""
    try:
        conn = _get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT title, body FROM content_table WHERE id = %s::uuid",
                    (content_id,),
                )
                row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Content not found")
            title = row["title"] or ""
            body = row["body"] or ""
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Content not found")

    analysis = call_gemini_realtime_analysis(
        title=title,
        body=body,
        user_role=request.user_role,
        user_industry=request.user_industry,
    )
    return RealTimeAnalysisResponse(analysis=analysis)


@router.get("/{content_id}")
def get_content_detail(content_id: str):
    """
    Return a single content_table row joined with engagement (via engagement_id FK)
    and the source name (via source_id FK).
    Falls back to a minimal response if DATABASE_URL is not set.
    """
    try:
        conn = _get_connection()
    except Exception:
        return {"id": content_id, "body": None, "url": None, "source_name": None,
                "published_at": None, "engagement": None}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    c.id::text,
                    c.body,
                    c.url,
                    c.published_at,
                    s.name AS source_name,
                    e.twitter_likes,
                    e.twitter_comments,
                    e.twitter_views,
                    e.twitter_reposts,
                    e.reddit_upvotes,
                    e.reddit_comments
                FROM content_table c
                LEFT JOIN sources s ON s.id = c.source_id
                LEFT JOIN engagement e ON e.id = c.engagement_id
                WHERE c.id = %s::uuid
                """,
                (content_id,),
            )
            row = cur.fetchone()

        if row is None:
            return {"id": content_id, "body": None, "url": None, "source_name": None,
                    "published_at": None, "engagement": None}

        engagement = None
        if row["twitter_likes"] is not None or row["reddit_upvotes"] is not None:
            engagement = {
                "twitter_likes": row["twitter_likes"] or 0,
                "twitter_comments": row["twitter_comments"] or 0,
                "twitter_views": row["twitter_views"] or 0,
                "twitter_reposts": row["twitter_reposts"] or 0,
                "reddit_upvotes": row["reddit_upvotes"] or 0,
                "reddit_comments": row["reddit_comments"] or 0,
            }

        return {
            "id": row["id"],
            "body": row["body"],
            "url": row["url"],
            "source_name": row["source_name"],
            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            "engagement": engagement,
        }
    finally:
        conn.close()
