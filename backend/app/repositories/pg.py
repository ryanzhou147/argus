from datetime import datetime
from typing import List, Optional

import psycopg2
import psycopg2.extras

from ..models.enums import EventType, RelationshipType
from .base import EventRepository

_UPDATABLE_FIELDS = {
    "canada_impact_summary",
    "summary",
    "confidence_score",
    "twitter_likes",
    "twitter_views",
    "twitter_comments",
    "twitter_reposts",
    "reddit_upvotes",
    "reddit_comments",
    "poly_volume",
    "poly_comments",
}

_ENGAGEMENT_FIELDS = {
    "twitter_likes",
    "twitter_views",
    "twitter_comments",
    "twitter_reposts",
    "reddit_upvotes",
    "reddit_comments",
    "poly_volume",
    "poly_comments",
}


def _row(cur) -> Optional[dict]:
    r = cur.fetchone()
    return dict(r) if r else None


def _rows(cur) -> List[dict]:
    return [dict(r) for r in cur.fetchall()]


class PostgresEventRepository(EventRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _conn(self):
        return psycopg2.connect(self._dsn, cursor_factory=psycopg2.extras.RealDictCursor)

    # ------------------------------------------------------------------
    # get_events
    # ------------------------------------------------------------------

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        clauses = []
        params = []
        if event_type:
            clauses.append("e.event_type = %s")
            params.append(event_type.value if hasattr(event_type, "value") else event_type)
        if start_time:
            clauses.append("e.start_time >= %s")
            params.append(start_time)
        if end_time:
            clauses.append("e.start_time <= %s")
            params.append(end_time)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT
                e.id,
                e.title,
                e.event_type,
                e.primary_latitude,
                e.primary_longitude,
                e.start_time,
                e.end_time,
                e.confidence_score,
                e.canada_impact_summary,
                c.image_url,
                c.s3_url AS image_s3_url
            FROM events e
            LEFT JOIN LATERAL (
                SELECT ct.image_url, ct.s3_url
                FROM event_content ec
                JOIN content_table ct ON ct.id = ec.content_item_id
                WHERE ec.event_id = e.id AND ct.image_url IS NOT NULL
                LIMIT 1
            ) c ON true
            {where}
            ORDER BY e.start_time DESC
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return _rows(cur)

    # ------------------------------------------------------------------
    # get_event_by_id
    # ------------------------------------------------------------------

    def get_event_by_id(self, event_id: str) -> Optional[dict]:
        sql = """
            SELECT
                e.id,
                e.title,
                e.event_type,
                e.primary_latitude,
                e.primary_longitude,
                e.start_time,
                e.end_time,
                e.confidence_score,
                e.canada_impact_summary,
                c.image_url,
                c.s3_url AS image_s3_url
            FROM events e
            LEFT JOIN LATERAL (
                SELECT ct.image_url, ct.s3_url
                FROM event_content ec
                JOIN content_table ct ON ct.id = ec.content_item_id
                WHERE ec.event_id = e.id AND ct.image_url IS NOT NULL
                LIMIT 1
            ) c ON true
            WHERE e.id = %s
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event_id,))
                return _row(cur)

    # ------------------------------------------------------------------
    # get_related_events
    # ------------------------------------------------------------------

    def get_related_events(self, event_id: str) -> List[dict]:
        sql = """
            SELECT
                er.event_b_id AS event_id,
                e.title,
                e.event_type,
                er.relationship_type,
                er.relationship_score,
                er.reason_codes AS reason,
                e.primary_latitude,
                e.primary_longitude
            FROM event_relationships er
            JOIN events e ON e.id = er.event_b_id
            WHERE er.event_a_id = %s
            UNION ALL
            SELECT
                er.event_a_id AS event_id,
                e.title,
                e.event_type,
                er.relationship_type,
                er.relationship_score,
                er.reason_codes AS reason,
                e.primary_latitude,
                e.primary_longitude
            FROM event_relationships er
            JOIN events e ON e.id = er.event_a_id
            WHERE er.event_b_id = %s
            ORDER BY relationship_score DESC
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event_id, event_id))
                return _rows(cur)

    # ------------------------------------------------------------------
    # get_filters
    # ------------------------------------------------------------------

    def get_filters(self) -> dict:
        return {
            "event_types": [t.value for t in EventType],
            "relationship_types": [t.value for t in RelationshipType],
        }

    # ------------------------------------------------------------------
    # get_timeline
    # ------------------------------------------------------------------

    def get_timeline(self) -> List[dict]:
        sql = """
            SELECT
                e.id,
                e.title,
                e.event_type,
                e.primary_latitude,
                e.primary_longitude,
                e.start_time,
                e.end_time,
                e.confidence_score,
                e.canada_impact_summary,
                c.image_url,
                c.s3_url AS image_s3_url
            FROM events e
            LEFT JOIN LATERAL (
                SELECT ct.image_url, ct.s3_url
                FROM event_content ec
                JOIN content_table ct ON ct.id = ec.content_item_id
                WHERE ec.event_id = e.id AND ct.image_url IS NOT NULL
                LIMIT 1
            ) c ON true
            ORDER BY e.start_time ASC
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return _rows(cur)

    # ------------------------------------------------------------------
    # get_event_detail
    # ------------------------------------------------------------------

    def get_event_detail(self, event_id: str) -> Optional[dict]:
        base = self.get_event_by_id(event_id)
        if base is None:
            return None

        with self._conn() as conn:
            with conn.cursor() as cur:
                # Summary from event row itself
                cur.execute("SELECT summary FROM events WHERE id = %s", (event_id,))
                row = _row(cur)
                base["summary"] = row["summary"] if row else ""

                # Source cards
                cur.execute(
                    """
                    SELECT
                        s.name AS source_name,
                        ct.title AS headline,
                        ct.published_at,
                        ct.url
                    FROM event_content ec
                    JOIN content_table ct ON ct.id = ec.content_item_id
                    LEFT JOIN sources s ON s.id = ct.source_id
                    WHERE ec.event_id = %s
                    ORDER BY ct.published_at DESC
                    """,
                    (event_id,),
                )
                base["sources"] = _rows(cur)

                # Entities via content items
                cur.execute(
                    """
                    SELECT DISTINCT ent.canonical_name
                    FROM event_content ec
                    JOIN content_entities ce ON ce.content_item_id = ec.content_item_id
                    JOIN entities ent ON ent.id = ce.entity_id
                    WHERE ec.event_id = %s
                    ORDER BY ent.canonical_name
                    LIMIT 10
                    """,
                    (event_id,),
                )
                base["entities"] = [r["canonical_name"] for r in _rows(cur)]

                # Related events
                base["related_events"] = self.get_related_events(event_id)

                # Engagement — look for engagement via content items
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(eng.reddit_upvotes), 0)  AS reddit_upvotes,
                        COALESCE(SUM(eng.reddit_comments), 0) AS reddit_comments,
                        COALESCE(SUM(eng.poly_volume), 0)     AS poly_volume,
                        COALESCE(SUM(eng.poly_comments), 0)   AS poly_comments,
                        COALESCE(SUM(eng.twitter_likes), 0)   AS twitter_likes,
                        COALESCE(SUM(eng.twitter_views), 0)   AS twitter_views,
                        COALESCE(SUM(eng.twitter_comments), 0) AS twitter_comments,
                        COALESCE(SUM(eng.twitter_reposts), 0) AS twitter_reposts
                    FROM event_content ec
                    JOIN content_table ct ON ct.id = ec.content_item_id
                    JOIN engagement eng ON eng.id = ct.engagement_id
                    WHERE ec.event_id = %s
                    """,
                    (event_id,),
                )
                eng_row = _row(cur)
                if eng_row and any(v for v in eng_row.values()):
                    base["engagement"] = {
                        "reddit_upvotes": int(eng_row["reddit_upvotes"]),
                        "reddit_comments": int(eng_row["reddit_comments"]),
                        "poly_volume": float(eng_row["poly_volume"]),
                        "poly_comments": int(eng_row["poly_comments"]),
                        "twitter_likes": int(eng_row["twitter_likes"]),
                        "twitter_views": int(eng_row["twitter_views"]),
                        "twitter_comments": int(eng_row["twitter_comments"]),
                        "twitter_reposts": int(eng_row["twitter_reposts"]),
                    }
                else:
                    base["engagement"] = None

        return base

    # ------------------------------------------------------------------
    # update_event_field
    # ------------------------------------------------------------------

    def update_event_field(self, event_id: str, field_name: str, new_value: object) -> dict:
        if field_name not in _UPDATABLE_FIELDS:
            return {
                "status": "failure",
                "message": f"Field '{field_name}' is not updatable. Allowed: {sorted(_UPDATABLE_FIELDS)}",
            }

        if field_name in _ENGAGEMENT_FIELDS:
            sql = f"""
                UPDATE engagement eng
                SET {field_name} = %s
                FROM content_table ct
                JOIN event_content ec ON ec.content_item_id = ct.id
                WHERE ct.engagement_id = eng.id AND ec.event_id = %s
            """
        else:
            sql = f"UPDATE events SET {field_name} = %s WHERE id = %s"

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_value, event_id))
                if cur.rowcount == 0:
                    conn.rollback()
                    return {"status": "failure", "message": f"Event '{event_id}' not found or no rows updated."}
            conn.commit()

        return {"status": "success", "event_id": event_id, "field_name": field_name, "new_value": new_value}

    # ------------------------------------------------------------------
    # search_events_by_text
    # ------------------------------------------------------------------

    def search_events_by_text(
        self,
        query: str,
        event_types: Optional[list] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[dict]:
        clauses = []
        params: list = []

        # Full-text search using pg to_tsvector
        clauses.append(
            "to_tsvector('english', COALESCE(e.title,'') || ' ' || COALESCE(e.summary,'') || ' ' || COALESCE(e.canada_impact_summary,'')) @@ plainto_tsquery('english', %s)"
        )
        params.append(query)

        if event_types:
            placeholders = ",".join(["%s"] * len(event_types))
            clauses.append(f"e.event_type IN ({placeholders})")
            params.extend(event_types)
        if start_time:
            clauses.append("e.start_time >= %s")
            params.append(start_time)
        if end_time:
            clauses.append("e.start_time <= %s")
            params.append(end_time)

        where = "WHERE " + " AND ".join(clauses)
        sql = f"""
            SELECT
                e.id,
                e.title,
                e.event_type,
                e.summary,
                e.canada_impact_summary,
                e.primary_latitude,
                e.primary_longitude,
                e.confidence_score,
                ts_rank(
                    to_tsvector('english', COALESCE(e.title,'') || ' ' || COALESCE(e.summary,'') || ' ' || COALESCE(e.canada_impact_summary,'')),
                    plainto_tsquery('english', %s)
                ) * 100 AS relevance_score
            FROM events e
            {where}
            ORDER BY relevance_score DESC
            LIMIT %s
        """
        params_full = [query] + params + [limit]

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params_full)
                rows = _rows(cur)

        # Attach key_entities per event
        if rows:
            event_ids = [r["id"] for r in rows]
            placeholders = ",".join(["%s"] * len(event_ids))
            entity_sql = f"""
                SELECT ec.event_id, ent.canonical_name
                FROM event_content ec
                JOIN content_entities ce ON ce.content_item_id = ec.content_item_id
                JOIN entities ent ON ent.id = ce.entity_id
                WHERE ec.event_id IN ({placeholders})
                ORDER BY ce.relevance_score DESC
            """
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(entity_sql, event_ids)
                    entity_rows = _rows(cur)

            entity_map: dict = {}
            for er in entity_rows:
                entity_map.setdefault(er["event_id"], [])
                if len(entity_map[er["event_id"]]) < 5:
                    entity_map[er["event_id"]].append(er["canonical_name"])

            for r in rows:
                r["key_entities"] = entity_map.get(r["id"], [])

        return rows
