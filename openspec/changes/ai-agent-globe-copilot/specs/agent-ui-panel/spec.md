## ADDED Requirements

### Requirement: Agent launcher button
The system SHALL display an agent chat icon button in the top-right corner of the main globe screen.

#### Scenario: Button visible on load
- **WHEN** the application loads
- **THEN** an agent launcher button SHALL be visible in the top-right corner

#### Scenario: Button opens agent panel
- **WHEN** the user clicks the agent launcher button
- **THEN** the agent query panel SHALL open

### Requirement: Agent query panel
The agent panel SHALL support: a free-text question input field, a submit button, a loading state while waiting for the backend response, and an answer display area.

#### Scenario: User submits query
- **WHEN** the user types a question and clicks submit (or presses Enter)
- **THEN** the panel SHALL show a loading state and send the query to `POST /agent/query`

#### Scenario: Loading state
- **WHEN** the agent query is in progress
- **THEN** the panel SHALL display a loading indicator and disable the submit button

### Requirement: Agent answer display
The agent panel SHALL display the agent's answer text, the confidence level, and the query type after receiving a response.

#### Scenario: Answer rendered
- **WHEN** the backend returns a valid agent response
- **THEN** the panel SHALL display the answer text and a confidence indicator (high/medium/low)

### Requirement: Confidence indicator
The agent panel SHALL display a visual confidence indicator that clearly distinguishes high, medium, and low confidence levels.

#### Scenario: High confidence display
- **WHEN** the response has `confidence: "high"`
- **THEN** the confidence indicator SHALL appear in a positive style (e.g., green)

#### Scenario: Low confidence display
- **WHEN** the response has `confidence: "low"`
- **THEN** the confidence indicator SHALL appear in a warning style (e.g., amber/red)

### Requirement: Caution banner
When the agent response includes a non-null `caution` field, the panel SHALL display an explicit caution banner warning the user.

#### Scenario: Caution shown for low confidence
- **WHEN** the response has `confidence: "low"` and a non-null `caution` message
- **THEN** the panel SHALL display a visible caution banner with the message text

#### Scenario: No caution for high confidence
- **WHEN** the response has `confidence: "high"` and `caution: null`
- **THEN** no caution banner SHALL be displayed

### Requirement: Related events list in panel
The agent panel SHALL display a list of surfaced related events based on `relevant_event_ids` in the response.

#### Scenario: Related events displayed
- **WHEN** the response includes `relevant_event_ids`
- **THEN** the panel SHALL list the corresponding event titles as clickable items

### Requirement: Cited external sources
When the response `mode` is `fallback_web`, the panel SHALL display cited external sources from `source_snippets` where `type` is `external`.

#### Scenario: External citations shown
- **WHEN** `mode` is `fallback_web` and `source_snippets` contains external sources
- **THEN** the panel SHALL display each external source with its name, headline, and clickable URL

#### Scenario: Internal mode hides external citations
- **WHEN** `mode` is `internal`
- **THEN** no external citation section SHALL be displayed

### Requirement: Financial impact section
When the agent response includes a non-null `financial_impact` object, the panel or modal SHALL display the financial impact summary, affected sectors, and impact direction.

#### Scenario: Financial impact displayed
- **WHEN** the response includes `financial_impact` with a summary
- **THEN** the panel SHALL display the impact summary, affected sectors as tags, and the impact direction indicator

### Requirement: Update result feedback
When the agent response `mode` is `update` and `update_result.status` is `success`, the panel SHALL display confirmation of the update with the field name and new value.

#### Scenario: Successful update feedback
- **WHEN** `update_result.status` is `success`
- **THEN** the panel SHALL display a success message with the updated field name and value

#### Scenario: Failed update feedback
- **WHEN** `update_result.status` is `failure`
- **THEN** the panel SHALL display the failure message from `update_result.message`

### Requirement: Reasoning steps display
The agent panel SHALL optionally display the reasoning steps from the response to help the user understand the agent's logic.

#### Scenario: Reasoning steps shown
- **WHEN** the response includes non-empty `reasoning_steps`
- **THEN** the panel SHALL display the steps in an expandable or collapsible section

### Requirement: Panel closable
The user SHALL be able to close the agent panel and return to the normal globe view.

#### Scenario: Close agent panel
- **WHEN** the user clicks the close button on the agent panel
- **THEN** the panel SHALL close and agent highlights on the globe SHALL remain until cleared by a new query or manual dismissal
