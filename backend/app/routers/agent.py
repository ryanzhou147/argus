from fastapi import APIRouter, HTTPException

from ..models.agent_schemas import AgentQueryRequest, AgentResponse
from ..services.agent_service import process_agent_query

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentResponse)
async def agent_query(request: AgentQueryRequest) -> AgentResponse:
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    return await process_agent_query(
        request.query.strip(),
        user_role=request.user_role,
        user_industry=request.user_industry,
    )
