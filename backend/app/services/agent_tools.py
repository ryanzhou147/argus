"""
Agent tool functions: direct DB queries against content_table + engagement.
Search strategy:
  1. Vector similarity (RAG) — embed the query with text-embedding-3-small and use
     pgvector cosine distance against pre-computed embeddings. Requires OPENAI_API_KEY.
  2. Keyword fallback — title ILIKE on extracted keywords (no API key needed).
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None  # type: ignore[assignment]


def _embed_query(text: str) -> list[float] | None:
    """Embed text with the same model used to build the stored vectors."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(model="text-embedding-3-small", input=text)
        return response.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding query failed: %s", exc)
        return None


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
    require_coords: bool = True,
) -> dict[str, Any]:
    try:
        conn = _get_connection()
    except Exception:
        return {"events": [], "total": 0}

    # Embed the query for vector similarity search (RAG)
    query_vec = _embed_query(query)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            type_clause = ""
            type_params: list[Any] = []
            if event_types:
                placeholders = ",".join(["%s"] * len(event_types))
                type_clause = f"AND event_type IN ({placeholders})"
                type_params = list(event_types)

            seen_ids: set[str] = set()
            rows: list[Any] = []

            _STOP = {"what", "how", "why", "when", "where", "who", "is", "are",
                     "was", "were", "the", "and", "for", "did", "has", "have",
                     "does", "will", "can", "about", "with", "this", "that", "its",
                     "explain", "tell", "show", "find", "give", "me", "us", "an", "on"}
            keywords = [w.strip("?.,!") for w in query.split()
                        if len(w.strip("?.,!")) > 2 and w.lower().strip("?.,!") not in _STOP]

            coord_clause = "AND latitude IS NOT NULL AND longitude IS NOT NULL" if require_coords else ""

            # ── STEP 1: keyword title match (always runs first) ──────────────
            # Seeds don't need globe coordinates — we need the most informative
            # articles, even if they have no lat/lng (those are still used as context).
            if keywords:
                # Exact phrase — highest precision, no coordinate requirement
                cur.execute(
                    f"""
                    SELECT id::text, title, body, url, event_type, latitude, longitude,
                           published_at, 1.0 AS rank
                    FROM content_table
                    WHERE title ILIKE %s
                      {coord_clause}
                      {type_clause}
                    ORDER BY published_at DESC LIMIT %s
                    """,
                    [f"%{query}%"] + type_params + [limit],
                )
                for r in cur.fetchall():
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"]); rows.append(r)

                # Keyword OR on title — score by how many keywords match
                if len(rows) < limit:
                    ilike_conds = " OR ".join(["title ILIKE %s"] * len(keywords))
                    # Count matching keywords as a relevance proxy
                    count_expr = " + ".join(
                        [f"(CASE WHEN title ILIKE %s THEN 1 ELSE 0 END)"] * len(keywords)
                    )
                    cur.execute(
                        f"""
                        SELECT id::text, title, body, url, event_type, latitude, longitude,
                               published_at,
                               ({count_expr})::float / {len(keywords)} AS rank
                        FROM content_table
                        WHERE ({ilike_conds})
                          {coord_clause}
                          {type_clause}
                        ORDER BY rank DESC, published_at DESC LIMIT %s
                        """,
                        [f"%{k}%" for k in keywords] * 2 + type_params + [limit],
                    )
                    for r in cur.fetchall():
                        if r["id"] not in seen_ids:
                            seen_ids.add(r["id"]); rows.append(r)

            # ── STEP 2: vector search fills remaining slots ───────────────────
            # Excluded: ACLED-style micro-events (body < 150 chars) which have
            # degenerate embeddings that pollute seed selection.
            if query_vec is not None and len(rows) < limit:
                remaining = limit - len(rows)
                vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
                cur.execute(
                    f"""
                    SELECT id::text, title, body, url, event_type, latitude, longitude,
                           published_at,
                           1 - (embedding <=> %s::vector) AS rank
                    FROM content_table
                    WHERE embedding IS NOT NULL
                      {coord_clause}
                      AND LENGTH(COALESCE(body, '')) > 150
                      {type_clause}
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s
                    """,
                    [vec_str, vec_str] + type_params + [remaining * 3],
                )
                for r in cur.fetchall():
                    if r["id"] not in seen_ids and len(rows) < limit:
                        seen_ids.add(r["id"]); rows.append(r)
                logger.info("After vector fill: %d total results for query: %s", len(rows), query[:60])

            rows = rows[:limit]

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
