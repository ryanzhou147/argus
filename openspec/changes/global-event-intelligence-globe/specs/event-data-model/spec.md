## ADDED Requirements

### Requirement: Sources table
The system SHALL maintain a `sources` table with fields: `id` (UUID, primary key), `name` (string), `type` (string), `base_url` (string), and `trust_score` (float 0.0–1.0).

#### Scenario: Source record exists
- **WHEN** a source is loaded into the system
- **THEN** it SHALL have a unique `id`, a non-empty `name`, a `type` value, a `base_url`, and a `trust_score` between 0.0 and 1.0

### Requirement: Content table
The system SHALL maintain a `content_table` with fields: `id` (UUID, primary key), `source_id` (UUID, foreign key to sources), `title` (string), `body` (string), `url` (string), `published_at` (datetime), `latitude` (float), `longitude` (float), `event_type` (EventType enum), `embedding` (vector, nullable), `sentiment_score` (float, nullable), `market_signal` (string, nullable), and `created_at` (datetime).

#### Scenario: Content row references a valid source
- **WHEN** a content row is retrieved
- **THEN** its `source_id` SHALL correspond to an existing source record

#### Scenario: Content row has valid coordinates
- **WHEN** a content row has `latitude` and `longitude`
- **THEN** `latitude` SHALL be between -90 and 90 and `longitude` SHALL be between -180 and 180

### Requirement: Entities table
The system SHALL maintain an `entities` table with fields: `id` (UUID, primary key), `name` (string), `canonical_name` (string), and `entity_type` (string).

#### Scenario: Entity has canonical name
- **WHEN** an entity is loaded
- **THEN** it SHALL have a non-empty `canonical_name` used for deduplication and display

### Requirement: Content-entities join table
The system SHALL maintain a `content_entities` table with fields: `content_item_id` (UUID, foreign key to content_table), `entity_id` (UUID, foreign key to entities), and `relevance_score` (float 0.0–1.0).

#### Scenario: Content-entity link exists
- **WHEN** a content-entity association is retrieved
- **THEN** both `content_item_id` and `entity_id` SHALL reference existing records and `relevance_score` SHALL be between 0.0 and 1.0

### Requirement: Events table
The system SHALL maintain an `events` table with fields: `id` (UUID, primary key), `title` (string), `summary` (string), `event_type` (EventType enum), `primary_latitude` (float), `primary_longitude` (float), `start_time` (datetime), `end_time` (datetime, nullable), `cluster_embedding` (vector, nullable), `canada_impact_summary` (string), and `confidence_score` (float 0.0–1.0).

#### Scenario: Event has valid geographic coordinates
- **WHEN** an event is retrieved
- **THEN** `primary_latitude` SHALL be between -90 and 90 and `primary_longitude` SHALL be between -180 and 180

#### Scenario: Event has Canada impact summary
- **WHEN** an event is retrieved
- **THEN** `canada_impact_summary` SHALL be a non-empty string explaining the event's relevance to Canada

### Requirement: Event-content join table
The system SHALL maintain an `event_content` table with fields: `event_id` (UUID, foreign key to events) and `content_item_id` (UUID, foreign key to content_table). Each event SHALL be linked to at least 2 content items.

#### Scenario: Event has linked content
- **WHEN** an event is retrieved with its content
- **THEN** it SHALL have at least 2 associated content items

### Requirement: Event relationships table
The system SHALL maintain an `event_relationships` table with fields: `id` (UUID, primary key), `event_a_id` (UUID, foreign key to events), `event_b_id` (UUID, foreign key to events), `relationship_type` (RelationshipType enum), `relationship_score` (float 0.0–1.0), and `reason_codes` (string or JSON).

#### Scenario: Relationship references valid events
- **WHEN** a relationship is retrieved
- **THEN** both `event_a_id` and `event_b_id` SHALL reference existing event records

#### Scenario: Valid relationship types
- **WHEN** a relationship is created
- **THEN** `relationship_type` SHALL be one of: `market_reaction`, `commodity_link`, `supply_chain_link`, `regional_spillover`, `policy_impact`, `same_event_family`

### Requirement: Engagement table
The system SHALL maintain an `engagement` table with fields: `id` (UUID, primary key), `reddit_upvotes` (integer), `reddit_comments` (integer), `poly_volume` (integer), and `poly_comments` (integer).

#### Scenario: Engagement metrics are non-negative
- **WHEN** an engagement record is retrieved
- **THEN** all numeric fields SHALL be non-negative integers

### Requirement: Six event types
The system SHALL define exactly six event types: `geopolitics`, `trade_supply_chain`, `energy_commodities`, `financial_markets`, `climate_disasters`, `policy_regulation`. These types SHALL be used across filters, seed data, event display, and API response typing.

#### Scenario: Event type validation
- **WHEN** an event or content item specifies an `event_type`
- **THEN** it SHALL be one of the six defined event types

### Requirement: Repository abstraction
The system SHALL define an abstract repository interface (`EventRepository`) with methods for querying events, content, entities, relationships, and engagement. A `MockEventRepository` SHALL implement this interface using in-memory seed data. The interface SHALL be designed so a `PostgresEventRepository` can replace it later without changing service or router code.

#### Scenario: Mock repository serves seeded data
- **WHEN** the application starts in local-demo mode
- **THEN** the mock repository SHALL return seeded data matching the production schema

#### Scenario: Repository interface is swappable
- **WHEN** a Postgres repository is implemented
- **THEN** it SHALL implement the same abstract interface as the mock repository and require no changes to service or router layers

### Requirement: Seed data volume
The seed data SHALL include: 8–10 sources, 40–60 content rows, 20–30 canonical entities, 18–24 clustered events, 30–50 event relationships, and engagement rows for surfaced events. Seed data SHALL represent plausible global stories (Red Sea shipping, OPEC changes, Fed/ECB decisions, wildfires, semiconductor controls, port strikes, sanctions, elections).

#### Scenario: Minimum seed data is present
- **WHEN** the mock repository is initialized
- **THEN** it SHALL contain at least 8 sources, 40 content rows, 20 entities, 18 events, 30 relationships, and engagement records for each event
