"""
Gemini client: one-shot function-calling orchestration.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..config import GEMINI_API_KEY, GEMINI_MODEL
from ..models.agent_schemas import (
    AgentResponse,
    ConfidenceLevel,
    FinancialImpact,
    HighlightRelationship,
    NavigationPlan,
    QueryType,
    SourceSnippet,
    UpdateResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool declarations for Gemini function calling
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = [
    {
        "name": "search_events",
        "description": "Search internal event graph by keyword. Returns candidate events with title, summary, canada_impact_summary, coordinates, and key entities.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or phrase"},
                "event_types": {"type": "array", "items": {"type": "string"}, "description": "Optional filter by event types"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_event_details",
        "description": "Get full details for a specific event by ID, including sources, entities, engagement, and related events.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "get_related_events",
        "description": "Get events related to a specific event, ordered by relationship score.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID"},
                "limit": {"type": "integer", "description": "Max related events to return"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "analyze_financial_impact",
        "description": "Generate a Canada-focused financial impact analysis for an event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID to analyze"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "update_mock_event_data",
        "description": "Update a specific field on an event in the mock data store. Only allowed fields: canada_impact_summary, summary, confidence_score, and engagement metrics.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID to update"},
                "field_name": {"type": "string", "description": "The field to update"},
                "new_value": {"type": "string", "description": "The new value (will be cast appropriately)"},
                "reason": {"type": "string", "description": "Reason for the update"},
            },
            "required": ["event_id", "field_name", "new_value"],
        },
    },
    {
        "name": "web_fallback_search",
        "description": "Search the web for external information when internal data is insufficient. Returns cited external sources.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Web search query"},
                "limit": {"type": "integer", "description": "Max results (default 3)"},
            },
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert geopolitical analyst specializing in global events and their impact on Canada.

You have access to an internal event intelligence graph with seeded real-world events. Always search internal data first.

When answering, you MUST return a valid JSON object conforming exactly to this schema:
{
  "answer": "string - comprehensive answer to the user's question",
  "confidence": "high" | "medium" | "low",
  "caution": "string or null - explain limitations if confidence is low",
  "mode": "internal" | "fallback_web" | "update",
  "query_type": "event_explanation" | "impact_analysis" | "connection_discovery" | "entity_relevance" | "update_request",
  "top_event_id": "string or null - primary event ID",
  "relevant_event_ids": ["array of relevant event IDs"],
  "highlight_relationships": [{"event_a_id": "string", "event_b_id": "string", "relationship_type": "string"}],
  "navigation_plan": {
    "center_on_event_id": "string or null",
    "zoom_level": "cluster" | "event" | null,
    "open_modal_event_id": "string or null",
    "pulse_event_ids": ["array of event IDs to pulse"]
  },
  "reasoning_steps": ["step 1", "step 2", ...],
  "financial_impact": null or {
    "summary": "string",
    "affected_sectors": ["list of sectors"],
    "impact_direction": "positive" | "negative" | "mixed" | "uncertain",
    "uncertainty_notes": "string or null"
  },
  "source_snippets": [],
  "update_result": null or {"status": "success"|"failure", "field_name": "string", "new_value": "string", "message": "string"}
}

Focus on Canada's perspective. Be specific about economic, trade, and geopolitical impacts on Canada."""


def _build_fallback_response(reason: str, query_type: QueryType = QueryType.event_explanation) -> AgentResponse:
    return AgentResponse(
        answer=f"I was unable to generate a complete analysis. {reason}",
        confidence=ConfidenceLevel.low,
        caution=reason,
        mode="internal",
        query_type=query_type,
        reasoning_steps=[reason],
    )


def call_gemini(
    query: str,
    tool_results: dict[str, Any],
    query_type: QueryType,
    use_web_fallback: bool = False,
) -> AgentResponse:
    """
    One-shot orchestration: send query + tool results to Gemini, parse structured response.
    Falls back gracefully if API is unavailable or response is invalid.
    """
    if not GEMINI_API_KEY:
        return AgentResponse(
            answer="The AI agent is currently unavailable. GEMINI_API_KEY is not configured.",
            confidence=ConfidenceLevel.low,
            caution="Agent unavailable: missing API key configuration. Internal data is still available via the globe.",
            mode="internal",
            query_type=query_type,
            reasoning_steps=["No GEMINI_API_KEY configured."],
        )

    try:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=GEMINI_API_KEY)

        # Build the user message with tool results embedded
        tool_context = json.dumps(tool_results, indent=2, default=str)
        user_message = (
            f"User question: {query}\n\n"
            f"Internal data retrieved:\n{tool_context}\n\n"
            f"Web fallback used: {use_web_fallback}\n\n"
            "Please analyze this data and return your structured JSON response."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        raw_text = response.text or ""
        return _parse_gemini_response(raw_text, query_type)

    except ImportError:
        logger.warning("google-genai not installed; returning fallback response")
        return _build_local_fallback(query, tool_results, query_type, use_web_fallback)
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return _build_local_fallback(query, tool_results, query_type, use_web_fallback)


def _parse_gemini_response(raw_text: str, query_type: QueryType) -> AgentResponse:
    try:
        data = json.loads(raw_text)
        # Coerce enums
        data["confidence"] = ConfidenceLevel(data.get("confidence", "low"))
        data["query_type"] = QueryType(data.get("query_type", query_type))

        if data.get("navigation_plan"):
            data["navigation_plan"] = NavigationPlan(**data["navigation_plan"])
        if data.get("financial_impact"):
            data["financial_impact"] = FinancialImpact(**data["financial_impact"])
        if data.get("highlight_relationships"):
            data["highlight_relationships"] = [
                HighlightRelationship(**r) for r in data["highlight_relationships"]
            ]
        if data.get("source_snippets"):
            data["source_snippets"] = [SourceSnippet(**s) for s in data["source_snippets"]]
        if data.get("update_result"):
            data["update_result"] = UpdateResult(**data["update_result"])

        return AgentResponse(**data)
    except Exception as exc:
        logger.error("Failed to parse Gemini response: %s\nRaw: %s", exc, raw_text[:500])
        return _build_fallback_response(f"Response parsing failed: {exc}", query_type)


def _build_local_fallback(
    query: str,
    tool_results: dict[str, Any],
    query_type: QueryType,
    use_web_fallback: bool,
) -> AgentResponse:
    """Generate a structured response from tool results without Gemini, for graceful degradation."""
    events = tool_results.get("search_results", {}).get("events", [])
    related = tool_results.get("related_events", {}).get("related_events", [])
    financial = tool_results.get("financial_impact")
    web_results = tool_results.get("web_results", {}).get("results", [])

    relevant_ids = [e["id"] for e in events[:5]]
    top_id = relevant_ids[0] if relevant_ids else None

    if events:
        event_summaries = "; ".join(e["title"] for e in events[:3])
        answer = (
            f"Based on internal event data, the following events are relevant to your query: {event_summaries}. "
            f"Canada impact: {events[0].get('canada_impact_summary', 'See event details for full impact analysis.')}"
        )
        confidence = ConfidenceLevel.medium
        caution = None
        mode = "internal"
    elif use_web_fallback and web_results:
        answer = f"No internal events matched your query. External sources suggest: {web_results[0]['headline']}"
        confidence = ConfidenceLevel.low
        caution = "Answer based on external sources only. Internal event data did not match this query."
        mode = "fallback_web"
    else:
        answer = "No relevant events found in the internal database for your query."
        confidence = ConfidenceLevel.low
        caution = "No internal data matched. Try rephrasing or broaden your search."
        mode = "internal"

    nav_plan = None
    if top_id:
        nav_plan = NavigationPlan(
            center_on_event_id=top_id,
            zoom_level="cluster" if len(relevant_ids) > 1 else "event",
            open_modal_event_id=top_id,
            pulse_event_ids=relevant_ids[:5],
        )

    fin_impact = None
    if financial and not financial.get("error"):
        fin_impact = FinancialImpact(
            summary=financial.get("impact_summary", ""),
            affected_sectors=financial.get("affected_sectors", []),
            impact_direction=financial.get("impact_direction", "uncertain"),
            uncertainty_notes=financial.get("uncertainty_notes"),
        )

    source_snippets = [
        SourceSnippet(source_name=r["source_name"], headline=r["headline"], url=r["url"], type="external")
        for r in web_results
    ]

    highlight_rels = []
    for r in related[:3]:
        if top_id:
            highlight_rels.append(HighlightRelationship(
                event_a_id=top_id,
                event_b_id=r.get("event_id", ""),
                relationship_type=r.get("relationship_type"),
            ))

    return AgentResponse(
        answer=answer,
        confidence=confidence,
        caution=caution,
        mode=mode,
        query_type=query_type,
        top_event_id=top_id,
        relevant_event_ids=relevant_ids,
        highlight_relationships=highlight_rels,
        navigation_plan=nav_plan,
        reasoning_steps=[
            f"Searched internal events for: {query}",
            f"Found {len(events)} matching events",
            "Generated answer from internal data" if events else "Fell back to web search",
        ],
        financial_impact=fin_impact,
        source_snippets=source_snippets,
    )
