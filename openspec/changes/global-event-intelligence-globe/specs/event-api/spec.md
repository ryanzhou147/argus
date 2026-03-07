## ADDED Requirements

### Requirement: GET /events endpoint
The system SHALL expose a `GET /events` endpoint that returns a list of events. The endpoint SHALL support optional query parameters: `event_type` (filter by EventType), `start_time` (ISO datetime, inclusive lower bound), and `end_time` (ISO datetime, inclusive upper bound).

#### Scenario: List all events
- **WHEN** a client sends `GET /events` with no parameters
- **THEN** the system SHALL return all seeded events with fields: `id`, `title`, `event_type`, `primary_latitude`, `primary_longitude`, `start_time`, `end_time`, `confidence_score`, `canada_impact_summary`, and `image_url`

#### Scenario: Filter events by type
- **WHEN** a client sends `GET /events?event_type=geopolitics`
- **THEN** the system SHALL return only events with `event_type` equal to `geopolitics`

#### Scenario: Filter events by time range
- **WHEN** a client sends `GET /events?start_time=2024-01-01T00:00:00Z&end_time=2024-06-01T00:00:00Z`
- **THEN** the system SHALL return only events whose `start_time` falls within the specified range

### Requirement: GET /events/{event_id} endpoint
The system SHALL expose a `GET /events/{event_id}` endpoint that returns the full modal payload for a single event.

#### Scenario: Retrieve full event detail
- **WHEN** a client sends `GET /events/{event_id}` with a valid event ID
- **THEN** the system SHALL return: `id`, `title`, `event_type`, `summary`, `primary_latitude`, `primary_longitude`, `start_time`, `end_time`, `canada_impact_summary`, `confidence_score`, `image_url`, source cards (source name, headline, publication time, URL), related events (title, relationship type, relationship score, reason), key entities (canonical name chips), and engagement snapshot (reddit_upvotes, reddit_comments, poly_volume, poly_comments)

#### Scenario: Event not found
- **WHEN** a client sends `GET /events/{event_id}` with a non-existent ID
- **THEN** the system SHALL return HTTP 404 with an error message

### Requirement: GET /events/{event_id}/related endpoint
The system SHALL expose a `GET /events/{event_id}/related` endpoint that returns related events and relationship metadata.

#### Scenario: Retrieve related events
- **WHEN** a client sends `GET /events/{event_id}/related` for an event with relationships
- **THEN** the system SHALL return a list of related events, each with: `event_id`, `title`, `event_type`, `relationship_type`, `relationship_score`, `reason`, `primary_latitude`, `primary_longitude`

#### Scenario: No related events
- **WHEN** a client sends `GET /events/{event_id}/related` for an event with no relationships
- **THEN** the system SHALL return an empty list

### Requirement: GET /filters endpoint
The system SHALL expose a `GET /filters` endpoint that returns supported filter options.

#### Scenario: Retrieve filter options
- **WHEN** a client sends `GET /filters`
- **THEN** the system SHALL return the list of supported event types and relationship types

### Requirement: GET /timeline endpoint
The system SHALL expose a `GET /timeline` endpoint that returns timeline data for playback.

#### Scenario: Retrieve timeline data
- **WHEN** a client sends `GET /timeline`
- **THEN** the system SHALL return events ordered by `start_time` with at minimum: `id`, `title`, `event_type`, `start_time`, `end_time`, `primary_latitude`, `primary_longitude`

### Requirement: Pydantic response models
All API responses SHALL be typed with Pydantic models. Response models SHALL match the TypeScript interfaces used by the frontend API client.

#### Scenario: Response serialization
- **WHEN** any API endpoint returns data
- **THEN** the response SHALL be serialized from a Pydantic model with proper field types and validation

### Requirement: CORS support
The FastAPI application SHALL include CORS middleware allowing requests from the Vite dev server origin (`http://localhost:5173`) during development.

#### Scenario: Frontend cross-origin request
- **WHEN** the frontend at `http://localhost:5173` sends a request to the backend at `http://localhost:8000`
- **THEN** the backend SHALL include appropriate CORS headers allowing the request

### Requirement: No authentication
The API SHALL NOT require any authentication. All endpoints SHALL be publicly accessible with no login, session, or token requirements.

#### Scenario: Unauthenticated access
- **WHEN** any client sends a request to any endpoint without credentials
- **THEN** the system SHALL process the request normally without returning 401 or 403
