## ADDED Requirements

### Requirement: POST /agent/query endpoint
The system SHALL expose a `POST /agent/query` endpoint that accepts a JSON body with a `query` string field and returns a structured agent response.

#### Scenario: Valid query submission
- **WHEN** a client sends `POST /agent/query` with `{"query": "Why did the Red Sea shipping disruption happen?"}`
- **THEN** the system SHALL return a JSON response conforming to the agent response schema with fields: `answer`, `confidence`, `caution`, `mode`, `query_type`, `top_event_id`, `relevant_event_ids`, `highlight_relationships`, `navigation_plan`, `reasoning_steps`, `financial_impact`, `source_snippets`, `update_result`

#### Scenario: Empty query
- **WHEN** a client sends `POST /agent/query` with `{"query": ""}`
- **THEN** the system SHALL return an error response with HTTP 400

### Requirement: Query classification
The agent pipeline SHALL classify each incoming query into one of five types: `event_explanation`, `impact_analysis`, `connection_discovery`, `entity_relevance`, `update_request`.

#### Scenario: Event explanation query
- **WHEN** the user asks "Why did the OPEC production cut happen?"
- **THEN** the system SHALL classify the query as `event_explanation`

#### Scenario: Impact analysis query
- **WHEN** the user asks "What is the financial impact of the Red Sea disruption on Canada?"
- **THEN** the system SHALL classify the query as `impact_analysis`

#### Scenario: Connection discovery query
- **WHEN** the user asks "What events are most related to the semiconductor export controls?"
- **THEN** the system SHALL classify the query as `connection_discovery`

#### Scenario: Entity relevance query
- **WHEN** the user asks "What does this mean for Canadian oil?"
- **THEN** the system SHALL classify the query as `entity_relevance`

#### Scenario: Update request query
- **WHEN** the user asks "Update the impact note for the OPEC event"
- **THEN** the system SHALL classify the query as `update_request`

### Requirement: Internal-first retrieval
The agent SHALL always attempt to retrieve relevant data from the internal event graph before considering web fallback. Internal retrieval SHALL use the `search_events`, `get_event_details`, and `get_related_events` tool functions.

#### Scenario: Sufficient internal data
- **WHEN** internal retrieval finds 2 or more relevant events with adequate evidence
- **THEN** the system SHALL synthesize the answer from internal data only and set `mode` to `internal`

#### Scenario: Insufficient internal data triggers web fallback
- **WHEN** internal retrieval finds fewer than 2 relevant events or evidence is weak
- **THEN** the system SHALL invoke `web_fallback_search` and set `mode` to `fallback_web`

### Requirement: Gemini function calling orchestration
The agent SHALL use Gemini 3 Flash via the `google-genai` SDK with function calling. The backend SHALL register six tool function declarations: `search_events`, `get_event_details`, `get_related_events`, `analyze_financial_impact`, `update_mock_event_data`, `web_fallback_search`. When Gemini requests a tool call, the backend SHALL execute the corresponding service function and return results to Gemini for synthesis.

#### Scenario: Gemini requests tool call
- **WHEN** Gemini's response includes a function call request for `search_events`
- **THEN** the backend SHALL execute the search_events service function with the provided arguments and feed the results back to Gemini

#### Scenario: Gemini synthesizes final answer
- **WHEN** Gemini has received all tool results
- **THEN** the backend SHALL extract the structured response from Gemini's output and validate it against the Pydantic response model

### Requirement: Structured JSON response
The agent response SHALL conform to a Pydantic model with exact field types as specified in the response schema. The backend SHALL validate the Gemini output against this model before returning to the frontend.

#### Scenario: Valid structured response
- **WHEN** Gemini returns a valid structured output
- **THEN** the backend SHALL return it as the API response with HTTP 200

#### Scenario: Invalid Gemini output fallback
- **WHEN** Gemini returns output that fails Pydantic validation
- **THEN** the backend SHALL return a fallback response with `confidence` set to `low`, a generic answer acknowledging the failure, and a caution message

### Requirement: Confidence and caution
The agent response SHALL include a `confidence` field (`high`, `medium`, or `low`) and an optional `caution` string. When confidence is `low`, the `caution` field SHALL contain an explanation of why evidence is weak.

#### Scenario: High confidence response
- **WHEN** internal data strongly supports the answer
- **THEN** `confidence` SHALL be `high` and `caution` SHALL be `null`

#### Scenario: Low confidence response
- **WHEN** evidence is weak or speculative
- **THEN** `confidence` SHALL be `low` and `caution` SHALL contain an explanation distinguishing likely drivers from possible drivers

### Requirement: search_events tool
The `search_events` tool SHALL accept `query`, optional `event_types`, optional `start_time`, optional `end_time`, and optional `limit` parameters. It SHALL return candidate events with title, summary, canada_impact_summary, coordinates, confidence, and key entities.

#### Scenario: Search with query only
- **WHEN** `search_events` is called with `query: "shipping disruption"`
- **THEN** it SHALL return events whose title or summary match the query, ranked by relevance

#### Scenario: Search with type filter
- **WHEN** `search_events` is called with `query: "oil"` and `event_types: ["energy_commodities"]`
- **THEN** it SHALL return only events matching both the query and the specified event types

### Requirement: get_event_details tool
The `get_event_details` tool SHALL accept an `event_id` and return the full event record with linked content, engagement snapshot, key entities, and related source summaries.

#### Scenario: Valid event details
- **WHEN** `get_event_details` is called with a valid event ID
- **THEN** it SHALL return the complete event detail payload

### Requirement: get_related_events tool
The `get_related_events` tool SHALL accept an `event_id` and optional `limit` and return related events with relationship type, relationship score, and reason codes.

#### Scenario: Related events found
- **WHEN** `get_related_events` is called for an event with relationships
- **THEN** it SHALL return the related events ordered by relationship score descending

### Requirement: analyze_financial_impact tool
The `analyze_financial_impact` tool SHALL accept an `event_id` and return a Canada-focused financial analysis with impact summary, affected Canadian sectors, confidence, and uncertainty notes.

#### Scenario: Financial impact analysis
- **WHEN** `analyze_financial_impact` is called for an event
- **THEN** it SHALL return an impact summary, list of affected sectors, impact direction (positive/negative/mixed/uncertain), and any uncertainty notes

### Requirement: update_mock_event_data tool
The `update_mock_event_data` tool SHALL accept `event_id`, `field_name`, `new_value`, and `reason`. It SHALL only allow updates to allowlisted fields: `canada_impact_summary`, `summary`, `confidence_score`, and engagement metrics. Updates SHALL be applied in-memory to the mock repository.

#### Scenario: Allowed field update
- **WHEN** `update_mock_event_data` is called with `field_name: "canada_impact_summary"` and a valid new value
- **THEN** the mock repository SHALL update the field in-memory and return `status: "success"` with the updated record snapshot

#### Scenario: Disallowed field update
- **WHEN** `update_mock_event_data` is called with a field not in the allowlist (e.g., `field_name: "id"`)
- **THEN** the system SHALL return `status: "failure"` with a validation message explaining the field is not updatable

### Requirement: web_fallback_search tool
The `web_fallback_search` tool SHALL accept a `query` and optional `limit`. It SHALL return summarized external results with source URLs and citations. It SHALL only be invoked when internal data is insufficient.

#### Scenario: Web fallback returns cited results
- **WHEN** `web_fallback_search` is called with a query
- **THEN** it SHALL return up to `limit` results, each with `source_name`, `headline`, `url`, and `type: "external"`

### Requirement: Gemini API key backend-only
The `GEMINI_API_KEY` environment variable SHALL be used only in the backend. The frontend SHALL NOT have access to the Gemini API key. If the key is missing, the agent endpoint SHALL return a structured error response indicating the agent is unavailable.

#### Scenario: Missing API key
- **WHEN** `GEMINI_API_KEY` is not set and a client sends `POST /agent/query`
- **THEN** the system SHALL return a response with `confidence: "low"` and a caution message stating the agent is unavailable due to missing configuration

### Requirement: No authentication on agent endpoint
The `POST /agent/query` endpoint SHALL NOT require authentication, consistent with the rest of the API.

#### Scenario: Unauthenticated agent access
- **WHEN** a client sends `POST /agent/query` without credentials
- **THEN** the system SHALL process the request normally
