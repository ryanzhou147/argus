## ADDED Requirements

### Requirement: Mock repository supports field-level updates
The `MockEventRepository` SHALL support updating individual fields on existing event records in-memory. Updates SHALL be restricted to an allowlist of fields: `canada_impact_summary`, `summary`, `confidence_score`, and engagement metrics. The update method SHALL validate the field name and value type before applying.

#### Scenario: Allowed field update succeeds
- **WHEN** the update method is called with a valid event ID, an allowlisted field name, and a value of the correct type
- **THEN** the field SHALL be updated in-memory and the method SHALL return the updated record

#### Scenario: Disallowed field update rejected
- **WHEN** the update method is called with a field name not in the allowlist
- **THEN** the method SHALL return a failure result with a validation message and the record SHALL remain unchanged

#### Scenario: Invalid event ID rejected
- **WHEN** the update method is called with a non-existent event ID
- **THEN** the method SHALL return a failure result indicating the event was not found

## MODIFIED Requirements

### Requirement: Engagement table
The system SHALL maintain an `engagement` table with fields: `id` (UUID, primary key), `reddit_upvotes` (integer), `reddit_comments` (integer), `poly_volume` (integer), `poly_comments` (integer), `twitter_likes` (integer), `twitter_views` (integer), `twitter_comments` (integer), and `twitter_reposts` (integer).

#### Scenario: Engagement metrics are non-negative
- **WHEN** an engagement record is retrieved
- **THEN** all numeric fields (including twitter_likes, twitter_views, twitter_comments, twitter_reposts) SHALL be non-negative integers

### Requirement: Repository abstraction
The system SHALL define an abstract repository interface (`EventRepository`) with methods for querying events, content, entities, relationships, and engagement, as well as a method for updating individual fields on existing event records. A `MockEventRepository` SHALL implement this interface using in-memory seed data. The interface SHALL be designed so a `PostgresEventRepository` can replace it later without changing service or router code.

#### Scenario: Mock repository serves seeded data
- **WHEN** the application starts in local-demo mode
- **THEN** the mock repository SHALL return seeded data matching the production schema

#### Scenario: Repository interface is swappable
- **WHEN** a Postgres repository is implemented
- **THEN** it SHALL implement the same abstract interface as the mock repository and require no changes to service or router layers

#### Scenario: Repository supports updates
- **WHEN** the update method is called on any repository implementation
- **THEN** it SHALL validate and apply the update according to the allowlist rules
