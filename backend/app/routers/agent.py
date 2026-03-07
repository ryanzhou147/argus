from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_repository
from ..models.agent_schemas import AgentQueryRequest, AgentResponse, ConfidenceLevel, QueryType
from ..repositories.base import EventRepository
from ..services.agent_service import process_agent_query

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentResponse)
async def agent_query(
    request: AgentQueryRequest,
    repo: EventRepository = Depends(get_repository),
) -> AgentResponse:
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    return await process_agent_query(request.query.strip(), repo)
