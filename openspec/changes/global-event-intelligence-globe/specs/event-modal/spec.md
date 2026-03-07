## ADDED Requirements

### Requirement: Modal displays event title and type
The event modal/side panel SHALL display the event's `title` and `event_type` prominently at the top.

#### Scenario: Title and type visible
- **WHEN** the modal opens for an event
- **THEN** the event title and event type SHALL be displayed

### Requirement: Modal displays location and time
The modal SHALL display the event's primary location (derived from coordinates or a location label) and its `start_time` with optional `end_time`.

#### Scenario: Location and time visible
- **WHEN** the modal opens for an event
- **THEN** the primary location and time range SHALL be displayed

### Requirement: Modal displays event summary
The modal SHALL display the event's `summary` as a concise event description.

#### Scenario: Summary visible
- **WHEN** the modal opens for an event
- **THEN** the event summary text SHALL be displayed

### Requirement: Modal displays Canada impact summary
The modal SHALL display the event's `canada_impact_summary` explaining why the event matters to Canada from a business and economic perspective.

#### Scenario: Canada impact visible
- **WHEN** the modal opens for an event
- **THEN** the Canada impact summary SHALL be displayed in a distinct section

### Requirement: Modal displays confidence score
The modal SHALL display the event's `confidence_score` as a visual indicator (e.g., percentage, bar, or badge).

#### Scenario: Confidence score visible
- **WHEN** the modal opens for an event
- **THEN** the confidence score SHALL be displayed

### Requirement: Modal displays hero image via Cloudinary
The modal SHALL render a hero image for the event using Cloudinary. The image SHALL be loaded using the event's Cloudinary public ID or URL through the media config layer.

#### Scenario: Hero image renders from Cloudinary
- **WHEN** the modal opens for an event with a valid Cloudinary public ID and Cloudinary credentials are configured
- **THEN** the hero image SHALL be rendered from Cloudinary with appropriate transformations

#### Scenario: Hero image fallback without Cloudinary
- **WHEN** the modal opens for an event but Cloudinary credentials are not configured
- **THEN** the system SHALL display a local placeholder image without crashing

### Requirement: Modal displays source cards
The modal SHALL display source cards from the event's underlying content items. Each source card SHALL show: source name, headline (content title), publication time, and URL.

#### Scenario: Source cards visible
- **WHEN** the modal opens for an event with linked content items
- **THEN** source cards SHALL be displayed with name, headline, publication time, and clickable URL

### Requirement: Modal displays related events
The modal SHALL display related events with: related event title, relationship type, relationship score, and a short reason.

#### Scenario: Related events visible
- **WHEN** the modal opens for an event with related events
- **THEN** related events SHALL be listed with title, type, score, and reason

### Requirement: Modal displays key entities
The modal SHALL display key entities as canonical entity chips derived from the event's linked content-entity associations.

#### Scenario: Entity chips visible
- **WHEN** the modal opens for an event with linked entities
- **THEN** canonical entity names SHALL be displayed as chips or tags

### Requirement: Modal displays engagement snapshot
The modal SHALL display an engagement snapshot with: `reddit_upvotes`, `reddit_comments`, `poly_volume`, `poly_comments`.

#### Scenario: Engagement metrics visible
- **WHEN** the modal opens for an event with engagement data
- **THEN** all four engagement metrics SHALL be displayed

### Requirement: Modal can be closed
The user SHALL be able to close the modal and return to the globe view.

#### Scenario: Close modal
- **WHEN** the user clicks the close button or presses Escape
- **THEN** the modal SHALL close and the globe SHALL be fully interactive again
