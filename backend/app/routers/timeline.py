from fastapi import APIRouter, Depends

from ..dependencies import get_repository
from ..models.schemas import TimelineResponse
from ..repositories.base import EventRepository
from ..services import event_service

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=TimelineResponse)
def get_timeline(repo: EventRepository = Depends(get_repository)):
    return event_service.get_timeline(repo)
