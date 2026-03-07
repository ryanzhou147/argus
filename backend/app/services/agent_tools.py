"""
Agent tool functions exposed to Gemini via function calling.
Each function receives the repository instance and tool arguments.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..repositories.base import EventRepository


def search_events(
    repo: "EventRepository",
    query: str,
    event_types: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    from datetime import datetime

    start_dt = None
    end_dt = None
    try:
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError:
        pass

    results = repo.search_events_by_text(
        query=query,
        event_types=event_types,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    return {"events": results, "total": len(results)}


def get_event_details(repo: "EventRepository", event_id: str) -> dict[str, Any]:
    detail = repo.get_event_detail(event_id)
    if detail is None:
        return {"error": f"Event '{event_id}' not found."}
    return detail


def get_related_events(
    repo: "EventRepository",
    event_id: str,
    limit: int = 5,
) -> dict[str, Any]:
    related = repo.get_related_events(event_id)
    # Sort by relationship_score descending
    related.sort(key=lambda r: r.get("relationship_score", 0), reverse=True)
    return {"related_events": related[:limit]}


def analyze_financial_impact(
    repo: "EventRepository",
    event_id: str,
) -> dict[str, Any]:
    detail = repo.get_event_detail(event_id)
    if detail is None:
        return {"error": f"Event '{event_id}' not found."}

    event_type = detail.get("event_type", "")
    canada_summary = detail.get("canada_impact_summary", "")
    summary = detail.get("summary", "")
    engagement = detail.get("engagement") or {}
    confidence = detail.get("confidence_score", 0.5)

    # Sector mapping heuristic
    sector_map = {
        "energy_commodities": ["Energy", "Oil & Gas", "Alberta Producers"],
        "trade_supply_chain": ["Retail", "Manufacturing", "Transportation"],
        "financial_markets": ["Banking", "Insurance", "Pension Funds"],
        "geopolitics": ["Defence", "Diplomacy", "Trade Policy"],
        "climate_disasters": ["Insurance", "Agriculture", "Real Estate"],
        "policy_regulation": ["Compliance", "Finance", "Technology"],
    }
    sectors = sector_map.get(event_type, ["General Economy"])

    # Direction heuristic based on sentiment in canada_summary
    impact_direction = "uncertain"
    neg_words = {"risk", "loss", "decline", "threat", "disruption", "increase", "higher cost", "burden"}
    pos_words = {"opportunity", "benefit", "growth", "boost", "gain", "advantage", "expand"}
    lower = (canada_summary + " " + summary).lower()
    neg_count = sum(1 for w in neg_words if w in lower)
    pos_count = sum(1 for w in pos_words if w in lower)
    if neg_count > pos_count:
        impact_direction = "negative"
    elif pos_count > neg_count:
        impact_direction = "positive"
    elif neg_count > 0 and pos_count > 0:
        impact_direction = "mixed"

    uncertainty_notes = None
    if confidence < 0.7:
        uncertainty_notes = "Analysis based on limited evidence; confidence below threshold."

    poly_volume = engagement.get("poly_volume", 0)
    market_signal = f"Polymarket volume: {poly_volume:,}" if poly_volume else None

    return {
        "event_id": event_id,
        "impact_summary": canada_summary,
        "affected_sectors": sectors,
        "impact_direction": impact_direction,
        "uncertainty_notes": uncertainty_notes,
        "market_signal": market_signal,
        "confidence": confidence,
    }


def update_mock_event_data(
    repo: "EventRepository",
    event_id: str,
    field_name: str,
    new_value: Any,
    reason: str = "",
) -> dict[str, Any]:
    result = repo.update_event_field(event_id, field_name, new_value)
    if reason:
        result["reason"] = reason
    return result


def web_fallback_search(
    query: str,
    limit: int = 3,
) -> dict[str, Any]:
    """
    Lightweight web fallback. Returns mock/placeholder external results.
    In production, replace with a real search API call.
    """
    results = [
        {
            "source_name": "Reuters",
            "headline": f"Global developments: {query[:60]}",
            "url": "https://www.reuters.com/search/news?query=" + query.replace(" ", "+"),
            "type": "external",
        },
        {
            "source_name": "Bloomberg",
            "headline": f"Market impact: {query[:60]}",
            "url": "https://www.bloomberg.com/search?query=" + query.replace(" ", "+"),
            "type": "external",
        },
        {
            "source_name": "Financial Times",
            "headline": f"Analysis: {query[:60]}",
            "url": "https://www.ft.com/search?q=" + query.replace(" ", "+"),
            "type": "external",
        },
    ]
    return {"results": results[:limit], "query": query}
