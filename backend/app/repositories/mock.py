import copy
from datetime import datetime, timezone
from typing import List, Optional

from ..data.seed_data import (
    CONTENT_ENTITIES,
    CONTENT_ITEMS,
    ENGAGEMENTS,
    ENTITIES,
    EVENT_CONTENT,
    EVENT_RELATIONSHIPS,
    EVENTS,
    SOURCES,
)
from ..models.enums import EventType, RelationshipType
from .base import EventRepository


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt


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


class MockEventRepository(EventRepository):
    def __init__(self) -> None:
        # Index seed data for O(1) lookups (deep copy so in-memory updates don't mutate module globals)
        self._sources = {s["id"]: s for s in SOURCES}
        self._content_items = {c["id"]: c for c in CONTENT_ITEMS}
        self._entities = {e["id"]: e for e in ENTITIES}
        self._events = {e["id"]: copy.deepcopy(e) for e in EVENTS}
        self._engagements = {e["event_id"]: e for e in ENGAGEMENTS}

        # Build reverse maps
        self._event_content: dict[str, list[str]] = {}  # event_id -> [content_ids]
        for ec in EVENT_CONTENT:
            self._event_content.setdefault(ec["event_id"], []).append(ec["content_item_id"])

        self._content_entities: dict[str, list[dict]] = {}  # content_id -> [{entity_id, relevance_score}]
        for ce in CONTENT_ENTITIES:
            self._content_entities.setdefault(ce["content_item_id"], []).append(ce)

        self._relationships: dict[str, list[dict]] = {}  # event_id -> [rel dicts]
        for r in EVENT_RELATIONSHIPS:
            self._relationships.setdefault(r["event_a_id"], []).append(r)
            # Relationships are bidirectional for display
            flipped = {**r, "event_a_id": r["event_b_id"], "event_b_id": r["event_a_id"]}
            self._relationships.setdefault(r["event_b_id"], []).append(flipped)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _event_to_dict(self, e: dict) -> dict:
        """Convert seed event dict to API-ready dict."""
        return {
            "id": e["id"],
            "title": e["title"],
            "event_type": e["event_type"],
            "primary_latitude": e["primary_latitude"],
            "primary_longitude": e["primary_longitude"],
            "start_time": _parse_dt(e["start_time"]),
            "end_time": _parse_dt(e.get("end_time")),
            "confidence_score": e["confidence_score"],
            "canada_impact_summary": e["canada_impact_summary"],
            "image_url": e.get("image_public_id"),
            "image_s3_url": None,
        }

    # ------------------------------------------------------------------
    # EventRepository implementation
    # ------------------------------------------------------------------

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        results = []
        for e in EVENTS:
            evt_start = _parse_dt(e["start_time"])
            if event_type and e["event_type"] != event_type:
                continue
            if start_time and evt_start < start_time:
                continue
            if end_time and evt_start > end_time:
                continue
            results.append(self._event_to_dict(e))
        return results

    def get_event_by_id(self, event_id: str) -> Optional[dict]:
        e = self._events.get(event_id)
        if e is None:
            return None
        return self._event_to_dict(e)

    def get_related_events(self, event_id: str) -> List[dict]:
        rels = self._relationships.get(event_id, [])
        results = []
        for r in rels:
            other_id = r["event_b_id"]
            other = self._events.get(other_id)
            if other is None:
                continue
            results.append({
                "event_id": other_id,
                "title": other["title"],
                "event_type": other["event_type"],
                "relationship_type": r["relationship_type"],
                "relationship_score": r["relationship_score"],
                "reason": r["reason_codes"],
                "primary_latitude": other["primary_latitude"],
                "primary_longitude": other["primary_longitude"],
            })
        return results

    def get_filters(self) -> dict:
        return {
            "event_types": [t.value for t in EventType],
            "relationship_types": [t.value for t in RelationshipType],
        }

    def get_timeline(self) -> List[dict]:
        events = [self._event_to_dict(e) for e in EVENTS]
        return sorted(events, key=lambda x: x["start_time"])

    def get_event_detail(self, event_id: str) -> Optional[dict]:
        e = self._events.get(event_id)
        if e is None:
            return None

        base = self._event_to_dict(e)
        base["summary"] = e["summary"]

        # Source cards from linked content items
        content_ids = self._event_content.get(event_id, [])
        source_cards = []
        for cid in content_ids:
            c = self._content_items.get(cid)
            if c is None:
                continue
            src = self._sources.get(c["source_id"])
            source_cards.append({
                "source_name": src["name"] if src else "Unknown",
                "headline": c["title"],
                "published_at": _parse_dt(c["published_at"]),
                "url": c["url"],
            })
        base["sources"] = source_cards

        # Entities: gather from all linked content items, deduplicate
        seen_entity_ids: set[str] = set()
        entity_names: list[str] = []
        for cid in content_ids:
            for ce in self._content_entities.get(cid, []):
                eid = ce["entity_id"]
                if eid not in seen_entity_ids:
                    seen_entity_ids.add(eid)
                    ent = self._entities.get(eid)
                    if ent:
                        entity_names.append(ent["canonical_name"])
        base["entities"] = entity_names

        # Related events
        base["related_events"] = self.get_related_events(event_id)

        # Engagement
        eng = self._engagements.get(event_id)
        if eng:
            base["engagement"] = {
                "reddit_upvotes": eng["reddit_upvotes"],
                "reddit_comments": eng["reddit_comments"],
                "poly_volume": float(eng["poly_volume"]),
                "poly_comments": eng["poly_comments"],
                "twitter_likes": eng.get("twitter_likes", 0),
                "twitter_views": eng.get("twitter_views", 0),
                "twitter_comments": eng.get("twitter_comments", 0),
                "twitter_reposts": eng.get("twitter_reposts", 0),
            }
        else:
            base["engagement"] = None

        return base

    def update_event_field(self, event_id: str, field_name: str, new_value: object) -> dict:
        if event_id not in self._events:
            return {"status": "failure", "message": f"Event '{event_id}' not found."}
        if field_name not in _UPDATABLE_FIELDS:
            return {
                "status": "failure",
                "message": f"Field '{field_name}' is not updatable. Allowed fields: {sorted(_UPDATABLE_FIELDS)}",
            }

        engagement_fields = {"twitter_likes", "twitter_views", "twitter_comments", "twitter_reposts",
                             "reddit_upvotes", "reddit_comments", "poly_volume", "poly_comments"}
        if field_name in engagement_fields:
            eng = self._engagements.get(event_id)
            if eng is None:
                return {"status": "failure", "message": f"No engagement record found for event '{event_id}'."}
            eng[field_name] = new_value
        else:
            self._events[event_id][field_name] = new_value

        return {
            "status": "success",
            "event_id": event_id,
            "field_name": field_name,
            "new_value": new_value,
        }

    def search_events_by_text(
        self,
        query: str,
        event_types: Optional[list] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[dict]:
        query_lower = query.lower()
        results = []
        for e in self._events.values():
            if event_types and e["event_type"] not in event_types:
                continue
            evt_start = _parse_dt(e["start_time"])
            if start_time and evt_start < start_time:
                continue
            if end_time and evt_start > end_time:
                continue

            searchable = " ".join([
                e.get("title", ""),
                e.get("summary", ""),
                e.get("canada_impact_summary", ""),
            ]).lower()

            # Token-based matching: split query into meaningful words (3+ chars)
            stop_words = {"the", "and", "for", "are", "was", "what", "how", "why",
                          "does", "did", "will", "can", "this", "that", "with", "from",
                          "have", "has", "had", "its", "but", "not", "you", "all",
                          "which", "been", "would", "could", "should"}
            tokens = [w for w in query_lower.split() if len(w) >= 3 and w not in stop_words]
            if not tokens:
                tokens = query_lower.split()

            match_count = sum(1 for t in tokens if t in searchable)
            if match_count == 0:
                continue

            score = match_count / len(tokens) * 100
            content_ids = self._event_content.get(e["id"], [])
            entity_names = []
            seen: set[str] = set()
            for cid in content_ids:
                for ce in self._content_entities.get(cid, []):
                    eid = ce["entity_id"]
                    if eid not in seen:
                        seen.add(eid)
                        ent = self._entities.get(eid)
                        if ent:
                            entity_names.append(ent["canonical_name"])

            results.append({
                "id": e["id"],
                "title": e["title"],
                "event_type": e["event_type"],
                "summary": e.get("summary", ""),
                "canada_impact_summary": e.get("canada_impact_summary", ""),
                "primary_latitude": e["primary_latitude"],
                "primary_longitude": e["primary_longitude"],
                "confidence_score": e["confidence_score"],
                "key_entities": entity_names[:5],
                "relevance_score": score,
            })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]
