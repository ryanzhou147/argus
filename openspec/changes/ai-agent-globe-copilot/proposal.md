## Why

The current MVP lets users visually explore event nodes, relationship arcs, and event modals, but understanding causality, relevance, and financial impact still requires manual inspection of the graph. Users need a natural-language interface that can interpret questions like "Why did X happen?", "What is the financial impact of Y on Canada?", or "Update the impact note for event A"—then retrieve relevant data, guide the globe UI cinematically, and answer with appropriate confidence signals.

## What Changes

- Add a one-shot AI agent accessible from a chat icon in the top-right corner of the globe screen.
- Add a backend `POST /agent/query` route that classifies user queries, retrieves internal event graph data, orchestrates Gemini 3 Flash via function calling and structured output, and returns a structured response with answer, confidence, navigation plan, and optional financial impact analysis.
- Add six internal tool functions exposed to Gemini: `search_events`, `get_event_details`, `get_related_events`, `analyze_financial_impact`, `update_mock_event_data`, `web_fallback_search`.
- Add frontend agent components: launcher button, query panel, answer view, navigation overlay, and financial impact modal section.
- Add cinematic globe navigation driven by agent responses: auto-center, zoom, pulse nodes, highlight arcs, auto-open modal.
- **BREAKING**: Change globe auto-spin behavior—auto-spin on load, stop on any user interaction, resume only after 5 minutes of inactivity.
- Add controlled mock-data update capability for local-demo mode (field-level updates to existing events via agent).
- Add web fallback search with cited external sources when internal data is insufficient.
- Extend engagement table with twitter metrics: `twitter_likes`, `twitter_views`, `twitter_comments`, `twitter_reposts`.
- Add `google-genai` Python SDK as a backend dependency.

## Capabilities

### New Capabilities
- `agent-query-orchestration`: Backend agent pipeline—query classification, internal retrieval, Gemini function calling, structured response generation, web fallback, and controlled mock-data updates.
- `agent-ui-panel`: Frontend agent launcher button, query panel, answer display, confidence indicators, caution banners, cited sources, and financial impact section.
- `agent-globe-navigation`: Cinematic globe control driven by agent responses—camera centering, zoom, node pulsing, arc highlighting, auto-modal opening, and sequenced multi-event focus.
- `agent-auto-spin`: Globe auto-spin lifecycle—spin on load, stop on interaction, resume after 5 minutes of inactivity.

### Modified Capabilities
- `globe-visualization`: Globe must support agent-driven camera control, node pulsing/highlighting, arc highlighting, and clearing of prior agent state.
- `event-data-model`: Engagement table gains four new twitter fields; mock repository must support field-level updates to existing event records.
- `event-modal`: Modal must include a new financial impact section when agent provides one.

## Impact

- **New backend dependency**: `google-genai` Python SDK; `GEMINI_API_KEY` environment variable required for agent features.
- **New API route**: `POST /agent/query` with structured JSON request/response.
- **Frontend new components**: `AgentLauncherButton`, `AgentPanel`, `AgentAnswerView`, `AgentNavigationOverlay`, `FinancialImpactModalSection`.
- **Modified frontend components**: `GlobeView` (camera control API, pulse/highlight state, auto-spin lifecycle), `EventModal` (financial impact section).
- **Modified backend**: `MockEventRepository` gains update method; engagement schema extended with twitter fields; seed data extended to include twitter engagement values.
- **No auth introduced**. No production DB writes. Controlled updates are local-demo-only against mock data.
