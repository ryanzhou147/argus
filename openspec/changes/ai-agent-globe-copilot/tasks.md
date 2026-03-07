## 1. Backend Dependencies & Configuration

- [x] 1.1 Add `google-genai` to `backend/requirements.txt`
- [x] 1.2 Add `GEMINI_API_KEY` to backend environment configuration and document in README
- [x] 1.3 Create `backend/app/config.py` with settings for GEMINI_API_KEY, model name (`gemini-3-flash-preview`), and agent defaults (confidence thresholds, max retrieval limit)

## 2. Data Model Updates

- [x] 2.1 Add `twitter_likes`, `twitter_views`, `twitter_comments`, `twitter_reposts` fields to the Engagement Pydantic model in `app/models/schemas.py`
- [x] 2.2 Update seed data engagement records in `app/data/seed_data.py` to include twitter metrics for every event
- [x] 2.3 Update frontend `Engagement` TypeScript interface in `src/types/events.ts` to include the four new twitter fields
- [x] 2.4 Update the event modal engagement snapshot component to render all eight engagement metrics (reddit + twitter)

## 3. Agent Pydantic Models

- [x] 3.1 Create `backend/app/models/agent_schemas.py` with request model (`AgentQueryRequest` with `query` string field)
- [x] 3.2 Create agent response Pydantic models: `AgentResponse`, `NavigationPlan`, `FinancialImpact`, `HighlightRelationship`, `SourceSnippet`, `UpdateResult`
- [x] 3.3 Define `QueryType` StrEnum: `event_explanation`, `impact_analysis`, `connection_discovery`, `entity_relevance`, `update_request`
- [x] 3.4 Define `ConfidenceLevel` StrEnum: `high`, `medium`, `low`

## 4. Repository Layer Updates

- [x] 4.1 Add abstract `update_event_field(event_id, field_name, new_value)` method to `EventRepository` base class in `app/repositories/base.py`
- [x] 4.2 Implement `update_event_field` in `MockEventRepository` with allowlist validation for: `canada_impact_summary`, `summary`, `confidence_score`, and engagement metrics
- [x] 4.3 Add a `search_events_by_text(query, event_types, start_time, end_time, limit)` method to the repository that performs simple keyword matching on event title, summary, and canada_impact_summary

## 5. Agent Tool Functions

- [x] 5.1 Create `backend/app/services/agent_tools.py` with `search_events` function that calls the repository search method and returns candidate events with title, summary, canada_impact_summary, coordinates, confidence, and key entities
- [x] 5.2 Implement `get_event_details` tool function that returns full event detail payload via the existing repository
- [x] 5.3 Implement `get_related_events` tool function that returns related events with relationship type, score, and reason codes
- [x] 5.4 Implement `analyze_financial_impact` tool function that generates a Canada-focused financial analysis from event and engagement data
- [x] 5.5 Implement `update_mock_event_data` tool function with field allowlist validation, calling the repository update method
- [x] 5.6 Implement `web_fallback_search` tool function that performs a lightweight web search (or Gemini grounding fallback) and returns cited results with source URLs

## 6. Gemini Integration

- [x] 6.1 Create `backend/app/services/gemini_client.py` with initialization of the `google-genai` client using `GEMINI_API_KEY`
- [x] 6.2 Define Gemini function declarations for all six tool functions matching their input/output schemas
- [x] 6.3 Implement the one-shot orchestration flow: send user query + tool declarations → receive tool call requests → execute tools → send tool results → receive structured response
- [x] 6.4 Implement structured output extraction and Pydantic validation of Gemini's response
- [x] 6.5 Implement fallback response generation when Gemini output fails validation or API is unavailable

## 7. Agent Service Layer

- [x] 7.1 Create `backend/app/services/agent_service.py` with the main `process_agent_query(query)` function
- [x] 7.2 Implement lightweight query classification (route to correct tool combination based on query intent)
- [x] 7.3 Implement internal-first retrieval logic with confidence gating (threshold check to decide if web fallback is needed)
- [x] 7.4 Implement update request handling: validate field, apply update via repository, return structured result
- [x] 7.5 Wire the full pipeline: classify → retrieve → call Gemini → validate response → return

## 8. Agent API Route

- [x] 8.1 Create `backend/app/routers/agent.py` with `POST /agent/query` endpoint accepting `AgentQueryRequest` and returning `AgentResponse`
- [x] 8.2 Handle empty query with HTTP 400 error
- [x] 8.3 Handle missing GEMINI_API_KEY gracefully with a structured low-confidence response
- [x] 8.4 Register agent router in `app/main.py`

## 9. Frontend Agent TypeScript Types

- [x] 9.1 Create `frontend/src/types/agent.ts` with TypeScript interfaces matching agent Pydantic models: `AgentResponse`, `NavigationPlan`, `FinancialImpact`, `HighlightRelationship`, `SourceSnippet`, `UpdateResult`, `QueryType`, `ConfidenceLevel`
- [x] 9.2 Add `postAgentQuery(query: string): Promise<AgentResponse>` function to the API client in `src/api/client.ts`

## 10. Agent React Context

- [x] 10.1 Create `frontend/src/context/AgentContext.tsx` with state: panel open/closed, current query, loading, agent response, active highlights, active navigation plan
- [x] 10.2 Expose actions: `submitQuery`, `clearAgentState`, `togglePanel`
- [x] 10.3 Wire `submitQuery` to call the API client and update state on response
- [x] 10.4 Add `AgentProvider` to the app's provider tree

## 11. Auto-Spin Lifecycle

- [x] 11.1 Add auto-spin state (spinning/stopped) and inactivity timer to the shared globe context or a new `AutoSpinContext`
- [x] 11.2 Implement: globe auto-spins on initial load
- [x] 11.3 Implement: any user interaction (mouse, keyboard, agent query, filter toggle, timeline scrub) stops auto-spin and resets 5-minute timer
- [x] 11.4 Implement: auto-spin resumes after 5 minutes of continuous inactivity
- [x] 11.5 Connect auto-spin state to the react-globe.gl `autoRotationSpeed` or equivalent prop

## 12. Agent UI Components

- [x] 12.1 Create `frontend/src/components/Agent/AgentLauncherButton.tsx` — chat icon button positioned in top-right corner
- [x] 12.2 Create `frontend/src/components/Agent/AgentPanel.tsx` — slide-out panel with text input, submit button, loading state, and answer area
- [x] 12.3 Create `frontend/src/components/Agent/AgentAnswerView.tsx` — renders answer text, confidence indicator (green/amber/red), caution banner, query type badge
- [x] 12.4 Implement reasoning steps display as an expandable/collapsible section in AgentAnswerView
- [x] 12.5 Implement related events list in the agent panel showing clickable event titles from `relevant_event_ids`
- [x] 12.6 Implement cited external sources section in the agent panel, shown only when `mode === "fallback_web"`
- [x] 12.7 Implement update result feedback display (success/failure message) in the agent panel
- [x] 12.8 Create `frontend/src/components/Agent/FinancialImpactSection.tsx` — displays impact summary, affected sector tags, impact direction indicator
- [x] 12.9 Implement close button for the agent panel

## 13. Agent-Driven Globe Navigation

- [x] 13.1 Create `frontend/src/components/Agent/AgentNavigationOverlay.tsx` or hook that reads the agent response and executes the navigation plan
- [x] 13.2 Implement: clear prior agent highlights when a new query response arrives
- [x] 13.3 Implement: stop auto-spin when agent navigation plan is received
- [x] 13.4 Implement: smooth camera animation to `center_on_event_id` coordinates
- [x] 13.5 Implement: zoom level control (`cluster` = wider view, `event` = tight zoom)
- [x] 13.6 Implement: pulse effect on `pulse_event_ids` nodes in the globe component
- [x] 13.7 Implement: highlight effect on arcs from `highlight_relationships` in the globe component
- [x] 13.8 Implement: auto-open event modal for `open_modal_event_id` after camera animation completes
- [x] 13.9 Implement: sequenced multi-event focus when multiple events are relevant (brief pauses between transitions)

## 14. Event Modal Updates

- [x] 14.1 Add `FinancialImpactSection` to the event modal, conditionally rendered when agent financial_impact data is present
- [x] 14.2 Ensure agent-opened modal scrolls to top
- [x] 14.3 Update engagement snapshot section to display all 8 metrics (reddit + twitter)

## 15. App Shell Integration

- [x] 15.1 Add `AgentLauncherButton` to the main app layout in the top-right corner
- [x] 15.2 Add `AgentPanel` as an overlay component in the app layout
- [x] 15.3 Wire globe component to read agent highlight/pulse/navigation state from AgentContext
- [x] 15.4 Wire event modal to read financial impact data from AgentContext when opened by agent

## 16. Integration & Polish

- [x] 16.1 Test end-to-end: submit agent query → backend returns structured response → globe navigates → nodes pulse → arcs highlight → modal opens → answer displays
- [x] 16.2 Test fallback: submit query outside internal data scope → web fallback triggers → external sources cited in panel
- [x] 16.3 Test update flow: submit update request → backend applies mock update → UI reflects change → success confirmation displayed
- [x] 16.4 Test missing GEMINI_API_KEY: agent returns graceful low-confidence response with caution
- [x] 16.5 Test auto-spin lifecycle: spins on load → stops on interaction → resumes after 5 min inactivity
- [x] 16.6 Verify Cloudinary media still renders correctly in event modals
- [x] 16.7 Update README with agent feature documentation, GEMINI_API_KEY setup, and example queries
