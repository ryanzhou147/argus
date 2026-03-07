## ADDED Requirements

### Requirement: ACLED API client fetches events from last N days
The system SHALL provide an ACLED HTTP client that fetches event records from the ACLED events API endpoint, filtered to the last `INGESTION_LOOKBACK_DAYS` days (default 14). The client SHALL authenticate using the `ACLED_API_TOKEN` environment variable. The client SHALL paginate through all available results.

#### Scenario: Successful fetch of recent ACLED events
- **WHEN** the ACLED client is invoked with a lookback of 14 days
- **THEN** the client sends authenticated GET requests to the ACLED events endpoint with date filters for the last 14 days and returns all paginated event records

#### Scenario: ACLED API token is missing
- **WHEN** the ACLED client is invoked without `ACLED_API_TOKEN` set
- **THEN** the client raises a configuration error with a descriptive message before making any HTTP requests

#### Scenario: ACLED API returns an error response
- **WHEN** the ACLED API returns a non-2xx status code
- **THEN** the client logs the error and raises an exception that the ingestion service can catch

### Requirement: ACLED normalizer maps events to NormalizedRecord
The system SHALL normalize each ACLED event record into a `NormalizedRecord` with these mappings:
- `title`: synthesized deterministic title from ACLED fields (event_type, country, location, date)
- `body`: best-available descriptive text assembled from event metadata (notes field and key metadata)
- `url`: ACLED source/native URL if present, otherwise a deterministic synthetic URL using source-native ID
- `published_at`: ACLED event date (mapped event timestamp, not article publication)
- `latitude`: ACLED latitude
- `longitude`: ACLED longitude
- `event_type`: normalized internal EventType via deterministic mapping
- `raw_metadata_json`: full ACLED record fields including `data_id` as `source_native_id`
- `embedding`, `sentiment_score`, `market_signal`: NULL

#### Scenario: Complete ACLED event record
- **WHEN** the normalizer receives a well-formed ACLED event with all fields present
- **THEN** it returns a `NormalizedRecord` with title synthesized from event_type/country/location/date, body from notes, coordinates from latitude/longitude, and event_type mapped from ACLED's event categories

#### Scenario: ACLED event with missing location coordinates
- **WHEN** the normalizer receives an ACLED event where latitude or longitude is missing or empty
- **THEN** it returns a `NormalizedRecord` with `latitude=NULL` and `longitude=NULL`

#### Scenario: ACLED event with no source URL
- **WHEN** the normalizer receives an ACLED event with no source URL field
- **THEN** it sets `url` to a deterministic synthetic URL using the ACLED `data_id`

#### Scenario: Malformed ACLED event record
- **WHEN** the normalizer receives an ACLED event missing critical fields (e.g., no data_id, no event_date)
- **THEN** it raises a normalization error that the ingestion service logs and skips

### Requirement: ACLED event type mapping is deterministic
The system SHALL map ACLED event categories to internal `EventType` values using a static mapping dictionary. If the ACLED category does not match any mapping key, the system SHALL default to `geopolitics`.

#### Scenario: Known ACLED event type
- **WHEN** the normalizer receives an ACLED event with event_type "Battles"
- **THEN** it maps to the corresponding internal EventType from the static mapping

#### Scenario: Unknown ACLED event type
- **WHEN** the normalizer receives an ACLED event with an unrecognized event_type value
- **THEN** it maps to `geopolitics` as the default

### Requirement: ACLED ingestion skips records older than lookback window
The system SHALL discard any ACLED event whose event_date is older than `INGESTION_LOOKBACK_DAYS` days from the current date, even if the API returns it.

#### Scenario: Event within lookback window
- **WHEN** an ACLED event has event_date 3 days ago and lookback is 14 days
- **THEN** the event is processed and normalized

#### Scenario: Event outside lookback window
- **WHEN** an ACLED event has event_date 20 days ago and lookback is 14 days
- **THEN** the event is discarded and not inserted

### Requirement: ACLED manual trigger via FastAPI route
The system SHALL expose a `POST /ingestion/acled` endpoint that triggers ACLED ingestion and returns a structured `RunSummary` JSON response.

#### Scenario: Successful ACLED ingestion via route
- **WHEN** a POST request is sent to `/ingestion/acled`
- **THEN** the system runs the ACLED ingestor and returns a RunSummary with source="acled", counts for fetched/inserted/duplicates_skipped/malformed_skipped/db_failures, timestamps, and status

### Requirement: ACLED manual trigger via CLI
The system SHALL support running `python -m app.ingestion.run_acled` to execute ACLED ingestion from the command line and print the RunSummary to stdout.

#### Scenario: CLI execution of ACLED ingestor
- **WHEN** a developer runs `python -m app.ingestion.run_acled` from the `backend/` directory
- **THEN** the ACLED ingestor executes, prints the RunSummary JSON to stdout, and exits with code 0 on success or 1 on failure
