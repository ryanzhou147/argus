"""
Agent service: graph-RAG pipeline for processing agent queries.

Pipeline:
  1. Embed query → find 2 seed articles (closest by cosine similarity)
  2. Graph-expand: for each seed, pull its arc-neighbors (pre-computed embedding neighbors)
  3. Deduplicate & pool all articles into one context blob
  4. Gemini reasons over the full context, with explicit Canada-impact instruction
"""
from __future__ import annotations

import re
from typing import Optional

from ..models.agent_schemas import AgentResponse, ConfidenceLevel, QueryType
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
    if any(k in q for k in ["impact", "effect", "affect", "cost", "financial", "economic", "price", "market", "trade"]):
        return QueryType.impact_analysis
    if any(k in q for k in ["related", "connection", "link", "connected", "relationship", "similar", "what events"]):
        return QueryType.connection_discovery
    if any(k in q for k in ["canadian", "canada", "sector", "industry", "oil", "energy", "bank", "dollar", "loonie"]):
        return QueryType.entity_relevance
    return QueryType.event_explanation


async def process_agent_query(
    query: str,
    user_role: Optional[str] = None,
    user_industry: Optional[str] = None,
) -> AgentResponse:
    query_type = _classify_query(query)

    # ── Step 1: find closest seeds — no coordinate requirement so we capture
    # informative articles even if they have no globe position ─────────────────
    seed_data = search_events(query, limit=3, require_coords=False)
    seeds = seed_data.get("events", [])

    # ── Step 2: graph-expand — pull arc-neighbors for each seed ───────────────
    # The arcs on the globe are cosine-similarity pairs from content_table.embedding.
    # get_related_events() uses the exact same pgvector distance to find neighbors.
    seen_ids: set[str] = {e["id"] for e in seeds}
    expanded_events = list(seeds)
    neighbor_graph: dict[str, list] = {}  # seed_id → its neighbors

    for seed in seeds:
        seed_id = seed["id"]
        related = get_related_events(seed_id, limit=6)
        neighbors = related.get("related_events", [])
        neighbor_graph[seed_id] = neighbors

        for n in neighbors:
            nid = n.get("event_id")
            if nid and nid not in seen_ids:
                seen_ids.add(nid)
                # Promote neighbor into the event list with its score
                expanded_events.append({
                    "id": nid,
                    "title": n.get("title", ""),
                    "summary": "",
                    "event_type": n.get("event_type", "geopolitics"),
                    "primary_latitude": n.get("primary_latitude"),
                    "primary_longitude": n.get("primary_longitude"),
                    "relevance_score": int(n.get("relationship_score", 0) * 100),
                })

    # ── Step 3: fetch full detail for seeds (body text for Gemini context) ────
    tool_results: dict = {
        "search_results": {"events": expanded_events, "total": len(expanded_events)},
        "graph_expansion": {
            "seeds": [s["id"] for s in seeds],
            "neighbor_graph": {
                sid: [{"event_id": n["event_id"], "title": n["title"], "score": n.get("relationship_score")}
                      for n in nbrs]
                for sid, nbrs in neighbor_graph.items()
            },
        },
    }

    for seed in seeds:
        detail = get_event_details(seed["id"])
        tool_results.setdefault("event_details", []).append(detail)

    # Financial impact for the top seed on impact queries
    if seeds and query_type == QueryType.impact_analysis:
        tool_results["financial_impact"] = analyze_financial_impact(seeds[0]["id"])

    # Web fallback only if we found nothing at all internally
    use_web_fallback = len(expanded_events) == 0
    if use_web_fallback:
        tool_results["web_results"] = web_fallback_search(query, limit=3)

    # Track which events have globe coordinates (can be navigated to)
    globe_ids: set[str] = {
        e["id"] for e in expanded_events
        if e.get("primary_latitude") is not None and e.get("primary_longitude") is not None
    }

    # ── Step 4: Gemini reasons over the full graph context ────────────────────
    response = call_gemini(query, tool_results, query_type, use_web_fallback, user_role=user_role, user_industry=user_industry)

    # ── Post-process: strip fields that would break globe navigation ──────────
    # Navigation plan fields must only reference events with coordinates.
    nav = response.navigation_plan
    if nav:
        center = nav.center_on_event_id if nav.center_on_event_id in globe_ids else None
        modal = nav.open_modal_event_id if nav.open_modal_event_id in globe_ids else center
        pulse = [pid for pid in nav.pulse_event_ids if pid in globe_ids]
        # If Gemini picked a non-coord center, fall back to first globe neighbor
        if center is None and pulse:
            center = pulse[0]
        from ..models.agent_schemas import NavigationPlan
        nav = NavigationPlan(
            center_on_event_id=center,
            zoom_level=nav.zoom_level,
            open_modal_event_id=modal,
            pulse_event_ids=pulse,
        )

    # relevant_event_ids: keep all (includes no-coord articles for the reference list)
    # but highlight_relationships must be globe-only (arcs need coordinates)
    hl = [r for r in response.highlight_relationships
          if r.event_a_id in globe_ids and r.event_b_id in globe_ids]

    # Strip financial_impact unless this was an impact query — Gemini freely adds it
    fin = response.financial_impact if query_type == QueryType.impact_analysis else None

    # Build cited_event_map: include both globe and no-coord articles so references work
    known_map = {e["id"]: e["title"] for e in expanded_events if e.get("id") and e.get("title")}
    merged_map = {**known_map, **response.cited_event_map}
    # Gemini sometimes emits [cite:uuid1, uuid2] — split each match on commas
    cited_in_text = {
        id_.strip()
        for raw in re.findall(r'\[cite:([^\]]+)\]', response.answer)
        for id_ in raw.split(',')
        if id_.strip()
    }
    relevant_set = set(response.relevant_event_ids)
    final_map = {k: v for k, v in merged_map.items() if k in cited_in_text or k in relevant_set}

    return response.model_copy(update={
        "navigation_plan": nav,
        "highlight_relationships": hl,
        "financial_impact": fin,
        "cited_event_map": final_map,
    })
