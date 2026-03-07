"""
Agent service: main pipeline for processing agent queries.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import AGENT_CONFIDENCE_THRESHOLD, AGENT_MIN_INTERNAL_RESULTS
from ..models.agent_schemas import AgentResponse, ConfidenceLevel, QueryType, UpdateResult
from .agent_tools import (
    analyze_financial_impact,
    get_event_details,
    get_related_events,
    search_events,
    update_mock_event_data,
    web_fallback_search,
)
from .gemini_client import call_gemini

if TYPE_CHECKING:
    from ..repositories.base import EventRepository


def _classify_query(query: str) -> QueryType:
    """Lightweight keyword-based query classification."""
    q = query.lower()

    update_keywords = ["update", "change", "set", "modify", "edit", "correct", "fix the"]
    if any(k in q for k in update_keywords):
        return QueryType.update_request

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


def _extract_event_id_from_query(query: str, search_results: list[dict]) -> str | None:
    """Try to identify a target event ID from the query and search results."""
    if search_results:
        return search_results[0]["id"]
    return None


async def process_agent_query(query: str, repo: "EventRepository") -> AgentResponse:
    """
    Full agent pipeline:
    1. Classify query type
    2. Internal retrieval (search + related + financial)
    3. Confidence gating → web fallback if needed
    4. Call Gemini with all tool results
    5. Handle update requests specially
    6. Return validated response
    """
    query_type = _classify_query(query)

    # Handle update requests
    if query_type == QueryType.update_request:
        return _handle_update_request(query, repo)

    # Internal retrieval
    search_results_data = search_events(repo, query, limit=10)
    events = search_results_data.get("events", [])

    # Confidence gating
    high_confidence_events = [
        e for e in events
        if e.get("relevance_score", 0) >= AGENT_CONFIDENCE_THRESHOLD
    ]
    use_web_fallback = len(high_confidence_events) < AGENT_MIN_INTERNAL_RESULTS

    tool_results: dict = {"search_results": search_results_data}

    # Get details + related for top event
    top_event_id = _extract_event_id_from_query(query, events)
    if top_event_id:
        detail = get_event_details(repo, top_event_id)
        tool_results["event_detail"] = detail

        related = get_related_events(repo, top_event_id, limit=5)
        tool_results["related_events"] = related

        if query_type == QueryType.impact_analysis:
            financial = analyze_financial_impact(repo, top_event_id)
            tool_results["financial_impact"] = financial

    # Web fallback
    if use_web_fallback:
        web_data = web_fallback_search(query, limit=3)
        tool_results["web_results"] = web_data

    return call_gemini(query, tool_results, query_type, use_web_fallback)


def _handle_update_request(query: str, repo: "EventRepository") -> AgentResponse:
    """
    Handle update_request queries by trying to extract event, field, and value from query.
    For demo purposes, returns a structured response indicating update capability.
    """
    from .gemini_client import _build_local_fallback

    # Search for the referenced event
    search_results_data = search_events(repo, query, limit=5)
    events = search_results_data.get("events", [])

    tool_results: dict = {"search_results": search_results_data}

    if events:
        top_event = events[0]
        event_id = top_event["id"]

        # Heuristic: detect field name from query
        field_name = None
        new_value = None
        q_lower = query.lower()

        if "canada impact" in q_lower or "canada_impact" in q_lower:
            field_name = "canada_impact_summary"
            # Extract value after "to" or quoted text
            import re
            match = re.search(r'(?:to|with|as)[:\s]+["\']?([^"\']+)["\']?$', query, re.IGNORECASE)
            if match:
                new_value = match.group(1).strip()

        if field_name and new_value and event_id:
            update_result_data = update_mock_event_data(repo, event_id, field_name, new_value, "Agent update request")
            tool_results["update_result"] = update_result_data

            update_result = UpdateResult(
                status=update_result_data["status"],
                field_name=field_name,
                new_value=str(new_value),
                message=update_result_data.get("message"),
            )

            return AgentResponse(
                answer=f"I've updated the '{field_name}' for event '{top_event['title']}' to: {new_value}",
                confidence=ConfidenceLevel.high,
                caution=None,
                mode="update",
                query_type=QueryType.update_request,
                top_event_id=event_id,
                relevant_event_ids=[event_id],
                reasoning_steps=[
                    f"Classified as update request",
                    f"Found target event: {top_event['title']}",
                    f"Updated field '{field_name}'",
                ],
                update_result=update_result,
            )

    return _build_local_fallback(query, tool_results, QueryType.update_request, False)
