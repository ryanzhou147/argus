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

You receive data from a graph-RAG pipeline:
- "search_results.events": the 2 semantically closest seed articles to the query, plus articles reachable via their embedding-similarity arcs
- "graph_expansion.neighbor_graph": which seed each neighbor came from and their similarity score
- "event_details": full body text of the seed articles

REASONING PROCESS — follow these steps explicitly in your reasoning_steps:
1. Identify the core event(s) from the seeds
2. Survey the neighbor articles — what related threads do they reveal?
3. FOR EACH relevant article: explicitly ask "How does this connect to Canada?" — consider trade flows, energy exports, military commitments, CAD exchange rate, immigration, commodity prices, Arctic sovereignty, supply chains, diplomatic posture
4. Synthesize a Canada-focused answer drawing on the strongest connections found

CITATION RULES:
- Cite events inline as [cite:EVENT_ID] using exact UUIDs from the data. Never invent IDs.
- Example: "Canada's decision to stay out [cite:abc-123] reflects its traditional NATO burden-sharing tension."
- Each [cite:...] tag must contain EXACTLY ONE UUID. Never put multiple IDs in one tag.
- WRONG: [cite:abc-123, def-456]  RIGHT: [cite:abc-123] [cite:def-456]
- Aim for 2-5 inline citations per answer.

When answering, return a valid JSON object with this exact schema:
{
  "answer": "string — Canada-focused answer with inline [cite:EVENT_ID] citations",
  "confidence": "high" | "medium" | "low",
  "caution": "string or null",
  "mode": "internal" | "fallback_web" | "update",
  "query_type": "event_explanation" | "impact_analysis" | "connection_discovery" | "entity_relevance" | "update_request",
  "top_event_id": "string or null — the single most relevant event ID",
  "relevant_event_ids": ["IDs of all events that matter to the answer, seeds + neighbors"],
  "highlight_relationships": [{"event_a_id": "string", "event_b_id": "string", "relationship_type": "string"}],
  "navigation_plan": {
    "center_on_event_id": "string or null",
    "zoom_level": "cluster" | "event" | null,
    "open_modal_event_id": "string or null",
    "pulse_event_ids": ["IDs to pulse on globe — seeds + most relevant neighbors"]
  },
  "reasoning_steps": ["step 1 — identify core event", "step 2 — survey neighbors", "step 3 — Canada links", "step 4 — synthesis"],
  "financial_impact": null or {"summary": "string", "affected_sectors": ["..."], "impact_direction": "positive|negative|mixed|uncertain", "uncertainty_notes": "string or null"},
  "source_snippets": [],
  "update_result": null,
  "cited_event_map": {"EVENT_ID": "Event Title for every ID cited above"}
}

Always ground your answer in the provided data. If a neighbor article strengthens or contradicts the seed, say so. Never omit the Canada angle."""


def _build_fallback_response(reason: str, query_type: QueryType = QueryType.event_explanation) -> AgentResponse:
    return AgentResponse(
        answer=f"I was unable to generate a complete analysis. {reason}",
        confidence=ConfidenceLevel.low,
        caution=reason,
        mode="internal",
        query_type=query_type,
        reasoning_steps=[reason],
    )


_ROLE_LABELS: dict[str, str] = {
    "general_user": "a general Canadian citizen",
    "academic": "a Canadian academic researcher",
    "investor": "a Canadian investor",
    "industry_leader": "a Canadian industry leader",
}

_INDUSTRY_LABELS: dict[str, str] = {
    "energy_resources": "Energy & Resources",
    "technology": "Technology",
    "financial_services": "Financial Services",
    "agriculture_food": "Agriculture & Food",
    "mining_minerals": "Mining & Minerals",
    "manufacturing": "Manufacturing",
    "healthcare_life_sciences": "Healthcare & Life Sciences",
    "transportation_logistics": "Transportation & Logistics",
}


def _build_persona_prompt(user_role: str | None, user_industry: str | None) -> str:
    role_label = _ROLE_LABELS.get(user_role or "general_user", "a general Canadian citizen")
    if user_role == "industry_leader" and user_industry:
        industry_label = _INDUSTRY_LABELS.get(user_industry, user_industry)
        return f"You are responding to {role_label} in the {industry_label} sector. Tailor your Canada-focused analysis to their professional interests and industry context."
    return f"You are responding to {role_label}. Tailor your Canada-focused analysis to their perspective."


def call_gemini(
    query: str,
    tool_results: dict[str, Any],
    query_type: QueryType,
    use_web_fallback: bool = False,
    user_role: str | None = None,
    user_industry: str | None = None,
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

        # Build a structured graph-context message for Gemini
        graph = tool_results.get("graph_expansion", {})
        seeds = graph.get("seeds", [])
        neighbor_graph = graph.get("neighbor_graph", {})
        all_events = tool_results.get("search_results", {}).get("events", [])
        event_details = tool_results.get("event_details", [])

        def _sanitize(text: str, max_len: int = 400) -> str:
            """Strip chars that break JSON string embedding."""
            return text[:max_len].replace('"', "'").replace("\n", " ").replace("\r", "").replace("\\", "/")

        # Seed summaries
        seed_lines = []
        for ev in all_events:
            if ev["id"] in seeds:
                detail = next((d for d in event_details if d.get("id") == ev["id"]), {})
                body_snippet = _sanitize(detail.get("summary") or "")
                seed_lines.append(
                    f'  • [{ev["id"]}] "{_sanitize(ev["title"], 120)}"\n'
                    f'    type={ev["event_type"]} | body: {body_snippet}'
                )

        # Neighbor summaries per seed
        neighbor_lines = []
        for sid, nbrs in neighbor_graph.items():
            for n in nbrs:
                nev = next((e for e in all_events if e["id"] == n["event_id"]), None)
                if nev:
                    neighbor_lines.append(
                        f'  • [{n["event_id"]}] "{_sanitize(n["title"], 100)}" (arc from seed {sid}, score={n.get("score", "?")})'
                    )

        user_message = (
            f"USER QUESTION: {query}\n\n"
            f"=== SEED ARTICLES (closest embedding match to query) ===\n"
            + ("\n".join(seed_lines) if seed_lines else "  (none found)")
            + f"\n\n=== NEIGHBOR ARTICLES (connected via arc similarity) ===\n"
            + ("\n".join(neighbor_lines) if neighbor_lines else "  (none)")
            + f"\n\n=== FULL CONTEXT JSON (IDs, coordinates, scores — no body text) ===\n"
            + json.dumps(
                {
                    k: (
                        # Strip body/summary from search_results to avoid JSON-breaking chars
                        {"events": [
                            {ek: ev[ek] for ek in ev if ek != "summary"}
                            for ev in v.get("events", [])
                        ], "total": v.get("total")}
                        if k == "search_results" else v
                    )
                    for k, v in tool_results.items() if k not in ("event_details",)
                },
                indent=2, default=str
            )
            + "\n\nNow apply your reasoning process and return the structured JSON response."
        )

        persona_prompt = _build_persona_prompt(user_role, user_industry)
        full_system_prompt = f"{SYSTEM_PROMPT}\n\n{persona_prompt}"

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=full_system_prompt,
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



def _extract_json(raw_text: str) -> dict:
    """Try increasingly lenient approaches to extract a JSON object from Gemini output."""
    # 1. Direct parse
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences (```json ... ```)
    import re
    stripped = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped.strip())
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3. Extract the outermost {...} block
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(raw_text[start:end])
        except json.JSONDecodeError:
            pass

    # 4. Replace literal \n inside strings (common Gemini issue)
    cleaned = re.sub(r'(?<!\\)\n(?=[^"]*"(?:[^"\\]|\\.)*")', " ", raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Could not parse JSON from Gemini response (len={len(raw_text)})")


def _parse_gemini_response(raw_text: str, query_type: QueryType) -> AgentResponse:
    try:
        data = _extract_json(raw_text)
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
        # cited_event_map is a plain dict – pass through as-is
        if not isinstance(data.get("cited_event_map"), dict):
            data["cited_event_map"] = {}

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

    cited_event_map = {e["id"]: e["title"] for e in events[:5] if e.get("id") and e.get("title")}

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
        cited_event_map=cited_event_map,
    )


def call_gemini_realtime_analysis(
    title: str,
    body: str,
    user_role: str | None = None,
    user_industry: str | None = None,
) -> str:
    """
    Call Gemini with Google Search grounding to produce a max-3-sentence
    persona-aware analysis of recent developments on the given event.
    Returns the analysis string, or raises on failure.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    persona_ctx = _build_persona_prompt(user_role, user_industry)

    body_snippet = body[:600].replace('"', "'").replace("\n", " ") if body else "(no body text)"

    prompt = (
        f"Event title: {title}\n"
        f"Background: {body_snippet}\n\n"
        f"{persona_ctx}\n\n"
        "Using Google Search, find the most recent news or developments related to this event. "
        "In at most 3 concise sentences, summarize what is new and how it affects Canada from this user's perspective. "
        "Be specific and grounded in real recent developments. Do not include citations or markdown."
    )

    try:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=0.4,
            ),
        )

        text = (response.text or "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")
        return text

    except ImportError:
        raise RuntimeError("google-genai not installed")
    except Exception as exc:
        logger.error("Gemini realtime analysis error: %s", exc)
        raise
