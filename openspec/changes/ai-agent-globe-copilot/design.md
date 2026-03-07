## Context

The existing MVP is a read-only 3D globe dashboard with event nodes, relationship arcs, timeline playback, event-type filtering, and a detail modal. The frontend is React 19 + Vite 6 + TypeScript 5 with react-globe.gl and Tailwind CSS, consuming a FastAPI backend that serves seeded mock data through a repository abstraction. Cloudinary handles event hero images.

The agent feature adds a natural-language query interface that retrieves internal event graph data, orchestrates an LLM (Gemini 3 Flash) to synthesize answers, and drives the globe UI cinematically. It also supports controlled mock-data updates and web fallback with citations.

Stakeholders: hackathon team, demo judges. The agent must work in local-demo mode without production infrastructure.

## Goals / Non-Goals

**Goals:**
- Deliver a one-shot agent that answers natural-language questions using internal event graph data first.
- Drive the globe UI cinematically in response to agent answers—center, zoom, pulse nodes, highlight arcs, auto-open modals.
- Use Gemini 3 Flash via function calling and structured output for reliable, machine-readable responses.
- Support five query types: event explanation, impact analysis, connection discovery, entity/sector relevance, and controlled data updates.
- Fall back to web search with cited sources when internal data is insufficient.
- Change globe auto-spin to stop on interaction and resume after 5 minutes of inactivity.

**Non-Goals:**
- Multi-turn conversation memory.
- Autonomous planning loops or background monitoring.
- Authentication or production database writes.
- Scraping or ingestion pipeline creation.
- Frontend-side LLM calls or exposed API keys.

## Decisions

### 1. One-shot orchestration via Gemini function calling

**Choice:** The backend receives a user query, classifies it, retrieves internal data, calls Gemini with tool definitions and tool results, and returns a single structured JSON response. No multi-turn agent loop.
**Rationale:** One-shot is simpler, more predictable, and sufficient for the five query types. Gemini's function calling lets the backend define tools (search_events, get_event_details, etc.) and receive structured tool-call requests, then provide results back for synthesis.
**Alternatives considered:** Multi-turn agent loop (too complex for v1, risk of runaway calls), direct prompt-only approach (loses tool-calling reliability), LangChain orchestration (unnecessary abstraction layer for 6 tools).

### 2. Gemini 3 Flash Preview as the model

**Choice:** Use `gemini-3-flash-preview` via the `google-genai` Python SDK.
**Rationale:** Low latency, supports function calling and structured output, suitable for routing and explanation tasks. The official Google GenAI SDK supports this model family with `GEMINI_API_KEY` environment variable.
**Alternatives considered:** GPT-4o (different provider, not requested), Gemini Pro (higher latency, unnecessary for this scope), local models (too slow, no function calling support).

### 3. Backend-only LLM access

**Choice:** All Gemini API calls happen in the FastAPI backend. The frontend only sends the user query string and receives the structured response.
**Rationale:** API key stays server-side. No secrets in the frontend bundle. Single point of control for rate limiting and error handling.
**Alternatives considered:** Frontend SDK calls (exposes API key), edge function proxy (adds infrastructure complexity).

### 4. Internal-first retrieval with confidence gating

**Choice:** The agent pipeline always attempts internal retrieval first. If internal search returns fewer than a threshold of relevant results (e.g., < 2 events with relevance above 0.5), the pipeline triggers web fallback search. The confidence level (high/medium/low) is determined by the number and quality of internal matches.
**Rationale:** Prioritizes the curated event graph. Web fallback is a safety net, not a primary source. Users see clear provenance indicators.
**Alternatives considered:** Always search both (wasteful, confusing provenance), web-only (defeats the purpose of the event graph).

### 5. Structured response schema drives frontend behavior

**Choice:** The `POST /agent/query` response includes: answer text, confidence level, caution message, navigation plan (center_on_event_id, zoom_level, open_modal_event_id, pulse_event_ids), relevant event/relationship IDs, financial impact analysis, source snippets, update result, and reasoning steps. The frontend executes the navigation plan declaratively.
**Rationale:** Decouples LLM reasoning from UI execution. The frontend doesn't interpret free text—it reads structured fields. This makes the cinematic navigation deterministic and testable.
**Alternatives considered:** Free-text response with frontend parsing (fragile), streaming with incremental UI updates (complex for v1).

### 6. Agent tools as backend service functions

**Choice:** Define six tool functions as Python service methods: `search_events`, `get_event_details`, `get_related_events`, `analyze_financial_impact`, `update_mock_event_data`, `web_fallback_search`. These are registered with Gemini as function declarations. When Gemini requests a tool call, the backend executes the corresponding service function and feeds results back.
**Rationale:** Reuses the existing repository layer. Tools are testable independently. The Gemini SDK's function calling protocol handles the tool call/response cycle.
**Alternatives considered:** Embedding all data in the prompt (token limit, no structure), separate microservices per tool (overkill).

### 7. Controlled mock-data updates via allowlist

**Choice:** The `update_mock_event_data` tool only allows updates to specific fields on existing events: `canada_impact_summary`, `summary`, `confidence_score`, and engagement metrics. Updates are applied in-memory to the mock repository. A validation layer checks field name and value type before applying.
**Rationale:** Prevents arbitrary mutation. Local-demo-only by design. The allowlist pattern is simple and safe.
**Alternatives considered:** Full CRUD (out of scope, risky), no updates at all (reduces demo impact for the "update X" query type).

### 8. Globe auto-spin lifecycle via inactivity timer

**Choice:** Globe auto-spins on initial load. Any user interaction (mouse, keyboard, agent query) stops auto-spin immediately and starts a 5-minute inactivity timer. When the timer fires without interruption, auto-spin resumes.
**Rationale:** Matches the requirement exactly. A single `useRef` timer in the globe context handles the lifecycle.
**Alternatives considered:** Never auto-spin after first interaction (less polished), configurable timeout (unnecessary complexity for v1).

### 9. Agent state in React context

**Choice:** Add an `AgentContext` provider that holds: agent panel open/closed, current query, loading state, agent response, and active highlights/navigation. The globe component reads highlight/navigation state from this context. The agent panel writes to it.
**Rationale:** Same pattern as the existing timeline/filter context. Keeps state centralized and avoids prop drilling across globe, modal, and agent panel.
**Alternatives considered:** Redux (overkill), Zustand (extra dependency), URL state (not suitable for transient agent state).

### 10. Web fallback via Gemini's grounding or simple fetch

**Choice:** For v1, implement web fallback as a simple backend function that performs a search query (using a lightweight search API or Gemini's built-in grounding if available) and returns summarized results with source URLs. The agent response marks `mode: "fallback_web"` and includes cited source snippets.
**Rationale:** Keeps the fallback simple and auditable. Citations are explicit. The frontend shows a distinct "external source" indicator.
**Alternatives considered:** SerpAPI (paid, extra dependency), Tavily (extra dependency), no fallback (reduces usefulness).

## Risks / Trade-offs

- **Gemini API latency** → Mitigated by using Flash (low-latency model) and one-shot orchestration. Show loading state in the UI.
- **Gemini API unavailability** → Mitigated by returning a structured error response with `confidence: "low"` and a caution message explaining the API is unreachable. App remains functional without agent.
- **Mock-data update persistence** → Updates are in-memory only and lost on backend restart. Acceptable for local-demo mode.
- **Web fallback quality** → External search results may be noisy. Mitigated by limiting to top 3 results and requiring Gemini to synthesize rather than pass through raw results.
- **Structured output reliability** → Gemini may occasionally deviate from the schema. Mitigated by Pydantic validation on the response with fallback to a generic error response.
- **Token limits** → Large event graphs could exceed context. Mitigated by limiting internal retrieval to top 10 candidates and summarizing content rather than including full bodies.
