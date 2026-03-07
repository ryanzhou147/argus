from fastapi import APIRouter, HTTPException
from ..embeddings.embedding_backfill_service import run_backfill

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/backfill/content")
async def backfill_content_embeddings():
    try:
        summary = await run_backfill()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
