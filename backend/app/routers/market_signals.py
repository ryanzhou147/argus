"""
Read-only endpoint that runs Polymarket and Kalshi scrapers and returns
normalized market signals. May be slow (live API calls to both platforms).
"""
from fastapi import APIRouter

from ..models.schemas import MarketSignal, MarketSignalsResponse
from ..services import scraping_service

router = APIRouter(prefix="/market-signals", tags=["market-signals"])


@router.get("", response_model=MarketSignalsResponse)
def get_market_signals() -> MarketSignalsResponse:
    """
    Fetch current market events from Polymarket and Kalshi using the
    integrated scrapers. Returns a combined, normalized list.
    Note: This endpoint performs live requests to external APIs and may be slow.
    """
    raw = scraping_service.fetch_all_market_signals()
    signals = [MarketSignal(**row) for row in raw]
    return MarketSignalsResponse(signals=signals, total=len(signals))
