from fastapi import APIRouter, Depends

from ..dependencies import get_repository
from ..models.schemas import FilterResponse
from ..repositories.base import EventRepository
from ..services import event_service

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("", response_model=FilterResponse)
def get_filters(repo: EventRepository = Depends(get_repository)):
    return event_service.get_filters(repo)
