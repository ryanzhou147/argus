## ADDED Requirements

### Requirement: Modal displays financial impact section
When the event modal is opened via an agent response that includes a non-null `financial_impact` object, the modal SHALL display a financial impact section with: impact summary, affected Canadian sectors as tags, and an impact direction indicator (positive/negative/mixed/uncertain).

#### Scenario: Financial impact shown from agent
- **WHEN** the modal opens for an event and the agent response includes `financial_impact` with a non-null summary
- **THEN** the modal SHALL display the financial impact section with summary text, sector tags, and direction indicator

#### Scenario: No financial impact section without agent data
- **WHEN** the modal opens for an event without an active agent response or with a null `financial_impact`
- **THEN** no financial impact section SHALL be displayed

### Requirement: Modal opened by agent auto-scrolls to top
When the modal is opened automatically by the agent navigation plan, it SHALL scroll to the top of the modal content.

#### Scenario: Agent-opened modal starts at top
- **WHEN** the agent navigation plan triggers the modal to open
- **THEN** the modal content SHALL be scrolled to the top

## MODIFIED Requirements

### Requirement: Modal displays engagement snapshot
The modal SHALL display an engagement snapshot with: `reddit_upvotes`, `reddit_comments`, `poly_volume`, `poly_comments`, `twitter_likes`, `twitter_views`, `twitter_comments`, and `twitter_reposts`.

#### Scenario: Engagement metrics visible
- **WHEN** the modal opens for an event with engagement data
- **THEN** all eight engagement metrics (reddit and twitter) SHALL be displayed
