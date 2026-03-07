from datetime import datetime
from typing import List, Optional

from ..models.enums import EventType
from ..models.schemas import (
    EngagementSnapshot,
    Event,
    EventDetail,
    EventListResponse,
    FilterResponse,
    RelatedEvent,
    RelatedEventsResponse,
    SourceCard,
    TimelineResponse,
)
from ..repositories.base import EventRepository


def list_events(
    repo: EventRepository,
    event_type: Optional[EventType] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> EventListResponse:
    raw = repo.get_events(event_type=event_type, start_time=start_time, end_time=end_time)
    events = [Event(**r) for r in raw]
    return EventListResponse(events=events, total=len(events))


def get_event_detail(repo: EventRepository, event_id: str) -> Optional[EventDetail]:
    raw = repo.get_event_detail(event_id)
    if raw is None:
        return None

    eng_raw = raw.pop("engagement", None)
    engagement = EngagementSnapshot(**eng_raw) if eng_raw else None

    sources = [SourceCard(**s) for s in raw.pop("sources", [])]
    related = [RelatedEvent(**r) for r in raw.pop("related_events", [])]
    entities = raw.pop("entities", [])

    return EventDetail(
        **raw,
        sources=sources,
        related_events=related,
        entities=entities,
        engagement=engagement,
    )


def get_related_events(repo: EventRepository, event_id: str) -> RelatedEventsResponse:
    raw = repo.get_related_events(event_id)
    related = [RelatedEvent(**r) for r in raw]
    return RelatedEventsResponse(related_events=related)


def get_filters(repo: EventRepository) -> FilterResponse:
    raw = repo.get_filters()
    return FilterResponse(**raw)


def get_timeline(repo: EventRepository) -> TimelineResponse:
    raw = repo.get_timeline()
    events = [Event(**r) for r in raw]
    if events:
        min_time = min(e.start_time for e in events)
        max_time = max(e.start_time for e in events)
    else:
        now = datetime.utcnow()
        min_time = max_time = now
    return TimelineResponse(events=events, min_time=min_time, max_time=max_time)
