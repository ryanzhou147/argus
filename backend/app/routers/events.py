from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_repository
from ..models.enums import EventType
from ..models.schemas import EventDetail, EventListResponse, RelatedEventsResponse
from ..repositories.base import EventRepository
from ..services import event_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
def list_events(
    event_type: Optional[EventType] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    repo: EventRepository = Depends(get_repository),
):
    return event_service.list_events(repo, event_type=event_type, start_time=start_time, end_time=end_time)


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: str, repo: EventRepository = Depends(get_repository)):
    detail = event_service.get_event_detail(repo, event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return detail


@router.get("/{event_id}/related", response_model=RelatedEventsResponse)
def get_related(event_id: str, repo: EventRepository = Depends(get_repository)):
    if repo.get_event_by_id(event_id) is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return event_service.get_related_events(repo, event_id)
