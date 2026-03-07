from fastapi import APIRouter, HTTPException
from ..ingestion.ingestion_service import run_acled_ingestion

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

@router.post("/acled")
async def ingest_acled():
    try:
        summary = await run_acled_ingestion()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
