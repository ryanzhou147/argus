"""
Agent tool functions: direct DB queries against content_table + engagement.
"""
from __future__ import annotations

import os
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None  # type: ignore[assignment]


def _get_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(url)


def search_events(
    query: str,
    event_types: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    try:
        conn = _get_connection()
    except Exception:
        return {"events": [], "total": 0}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conditions = ["(title ILIKE %s OR body ILIKE %s)"]
            params: list[Any] = [f"%{query}%", f"%{query}%"]

            if event_types:
                placeholders = ",".join(["%s"] * len(event_types))
                conditions.append(f"event_type IN ({placeholders})")
                params.extend(event_types)

            where = " AND ".join(conditions)
            cur.execute(
                f"""
                SELECT id::text, title, body, url, event_type, latitude, longitude,
                       published_at
                FROM content_table
                WHERE {where}
                  AND latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY published_at DESC
                LIMIT %s
                """,
                params + [limit],
            )
            rows = cur.fetchall()

        results = [
            {
                "id": r["id"],
                "title": r["title"] or "",
                "summary": r["body"] or "",
                "event_type": r["event_type"] or "geopolitics",
                "primary_latitude": r["latitude"],
                "primary_longitude": r["longitude"],
                "relevance_score": 80,
            }
            for r in rows
        ]
        return {"events": results, "total": len(results)}
    finally:
        conn.close()


def get_event_details(event_id: str) -> dict[str, Any]:
    try:
        conn = _get_connection()
    except Exception:
        return {"error": "Database unavailable"}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT c.id::text, c.title, c.body, c.url, c.event_type,
                       c.latitude, c.longitude, c.published_at,
                       s.name AS source_name,
                       e.twitter_likes, e.reddit_upvotes, e.poly_volume
                FROM content_table c
                LEFT JOIN sources s ON s.id = c.source_id
                LEFT JOIN engagement e ON e.id = c.engagement_id
                WHERE c.id = %s::uuid
                """,
                (event_id,),
            )
            row = cur.fetchone()

        if row is None:
            return {"error": f"Event '{event_id}' not found."}

        return {
            "id": row["id"],
            "title": row["title"],
            "summary": row["body"],
            "url": row["url"],
            "event_type": row["event_type"],
            "primary_latitude": row["latitude"],
            "primary_longitude": row["longitude"],
            "canada_impact_summary": "",
            "confidence_score": 0.75,
            "engagement": {
                "twitter_likes": row["twitter_likes"] or 0,
                "reddit_upvotes": row["reddit_upvotes"] or 0,
                "poly_volume": float(row["poly_volume"] or 0),
            },
        }
    finally:
        conn.close()


def get_related_events(event_id: str, limit: int = 5) -> dict[str, Any]:
    """Return events with similar embeddings using pgvector cosine distance."""
    try:
        conn = _get_connection()
    except Exception:
        return {"related_events": []}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, title, event_type, latitude, longitude,
                       embedding <=> (SELECT embedding FROM content_table WHERE id = %s::uuid) AS distance
                FROM content_table
                WHERE id != %s::uuid
                  AND embedding IS NOT NULL
                  AND latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY distance ASC
                LIMIT %s
                """,
                (event_id, event_id, limit),
            )
            rows = cur.fetchall()

        return {
            "related_events": [
                {
                    "event_id": r["id"],
                    "title": r["title"],
                    "event_type": r["event_type"],
                    "primary_latitude": r["latitude"],
                    "primary_longitude": r["longitude"],
                    "relationship_score": round(1 - float(r["distance"]), 3),
                }
                for r in rows
            ]
        }
    finally:
        conn.close()


def analyze_financial_impact(event_id: str) -> dict[str, Any]:
    detail = get_event_details(event_id)
    if "error" in detail:
        return detail

    event_type = detail.get("event_type", "")
    summary = detail.get("summary", "") or ""

    sector_map = {
        "energy_commodities": ["Energy", "Oil & Gas", "Alberta Producers"],
        "trade_supply_chain": ["Retail", "Manufacturing", "Transportation"],
        "financial_markets": ["Banking", "Insurance", "Pension Funds"],
        "geopolitics": ["Defence", "Diplomacy", "Trade Policy"],
        "climate_disasters": ["Insurance", "Agriculture", "Real Estate"],
        "policy_regulation": ["Compliance", "Finance", "Technology"],
    }
    sectors = sector_map.get(event_type, ["General Economy"])

    neg_words = {"risk", "loss", "decline", "threat", "disruption", "higher cost", "burden"}
    pos_words = {"opportunity", "benefit", "growth", "boost", "gain", "advantage", "expand"}
    lower = summary.lower()
    neg_count = sum(1 for w in neg_words if w in lower)
    pos_count = sum(1 for w in pos_words if w in lower)
    if neg_count > pos_count:
        impact_direction = "negative"
    elif pos_count > neg_count:
        impact_direction = "positive"
    elif neg_count > 0 and pos_count > 0:
        impact_direction = "mixed"
    else:
        impact_direction = "uncertain"

    poly_volume = detail.get("engagement", {}).get("poly_volume", 0)

    return {
        "event_id": event_id,
        "impact_summary": summary[:300] if summary else None,
        "affected_sectors": sectors,
        "impact_direction": impact_direction,
        "uncertainty_notes": None,
        "market_signal": f"Polymarket volume: {poly_volume:,.0f}" if poly_volume else None,
        "confidence": 0.75,
    }


def web_fallback_search(query: str, limit: int = 3) -> dict[str, Any]:
    results = [
        {
            "source_name": "Reuters",
            "headline": f"Global developments: {query[:60]}",
            "url": "https://www.reuters.com/search/news?query=" + query.replace(" ", "+"),
            "type": "external",
        },
        {
            "source_name": "Bloomberg",
            "headline": f"Market impact: {query[:60]}",
            "url": "https://www.bloomberg.com/search?query=" + query.replace(" ", "+"),
            "type": "external",
        },
        {
            "source_name": "Financial Times",
            "headline": f"Analysis: {query[:60]}",
            "url": "https://www.ft.com/search?q=" + query.replace(" ", "+"),
            "type": "external",
        },
    ]
    return {"results": results[:limit], "query": query}
