"""
Agent service: main pipeline for processing agent queries.
"""
from __future__ import annotations

from ..config import AGENT_CONFIDENCE_THRESHOLD, AGENT_MIN_INTERNAL_RESULTS
from ..models.agent_schemas import AgentResponse, ConfidenceLevel, QueryType, UpdateResult
from .agent_tools import (
    analyze_financial_impact,
    get_event_details,
    get_related_events,
    search_events,
    web_fallback_search,
)
from .gemini_client import call_gemini


def _classify_query(query: str) -> QueryType:
    q = query.lower()

    impact_keywords = ["impact", "effect", "affect", "cost", "financial", "economic", "price", "market", "trade"]
    if any(k in q for k in impact_keywords):
        return QueryType.impact_analysis

    connection_keywords = ["related", "connection", "link", "connected", "relationship", "similar", "what events"]
    if any(k in q for k in connection_keywords):
        return QueryType.connection_discovery

    entity_keywords = ["canadian", "canada", "sector", "industry", "oil", "energy", "bank", "dollar", "loonie"]
    if any(k in q for k in entity_keywords):
        return QueryType.entity_relevance

    return QueryType.event_explanation


async def process_agent_query(query: str) -> AgentResponse:
    query_type = _classify_query(query)

    search_results_data = search_events(query, limit=10)
    events = search_results_data.get("events", [])

    high_confidence_events = [
        e for e in events
        if e.get("relevance_score", 0) >= AGENT_CONFIDENCE_THRESHOLD
    ]
    use_web_fallback = len(high_confidence_events) < AGENT_MIN_INTERNAL_RESULTS

    tool_results: dict = {"search_results": search_results_data}

    top_event_id = events[0]["id"] if events else None
    if top_event_id:
        detail = get_event_details(top_event_id)
        tool_results["event_detail"] = detail

        related = get_related_events(top_event_id, limit=5)
        tool_results["related_events"] = related

        if query_type == QueryType.impact_analysis:
            financial = analyze_financial_impact(top_event_id)
            tool_results["financial_impact"] = financial

    if use_web_fallback:
        web_data = web_fallback_search(query, limit=3)
        tool_results["web_results"] = web_data

    return call_gemini(query, tool_results, query_type, use_web_fallback)
