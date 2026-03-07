from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..models.enums import EventType

class NormalizedRecord(BaseModel):
    """Internal model representing a normalized API record ready for DB insertion."""
    source_native_id: str
    title: str
    body: str
    url: str
    published_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    event_type: EventType
    raw_metadata_json: Dict[str, Any]

class RunSummary(BaseModel):
    """Structured summary of an ingestion run."""
    source: str  # "acled", "reliefweb", or "all"
    lookback_days: int
    fetched: int = 0
    inserted: int = 0
    duplicates_skipped: int = 0
    malformed_skipped: int = 0
    db_failures: int = 0
    started_at: datetime
    finished_at: datetime
    status: str  # "success", "partial_success", "failure"
