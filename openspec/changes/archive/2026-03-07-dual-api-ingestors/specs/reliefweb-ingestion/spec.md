## ADDED Requirements

### Requirement: ReliefWeb API client fetches reports from last N days
The system SHALL provide a ReliefWeb HTTP client that fetches report records from the ReliefWeb Reports API v1 endpoint, filtered to the last `INGESTION_LOOKBACK_DAYS` days (default 14). The client SHALL include the `RELIEFWEB_APPNAME` in requests as required by the API. The client SHALL paginate through all available results.

#### Scenario: Successful fetch of recent ReliefWeb reports
- **WHEN** the ReliefWeb client is invoked with a lookback of 14 days
- **THEN** the client sends requests to the ReliefWeb Reports endpoint with date filters for the last 14 days, includes the appname header/parameter, and returns all paginated report records

#### Scenario: ReliefWeb appname is missing
- **WHEN** the ReliefWeb client is invoked without `RELIEFWEB_APPNAME` set
- **THEN** the client raises a configuration error with a descriptive message before making any HTTP requests

#### Scenario: ReliefWeb API returns an error response
- **WHEN** the ReliefWeb API returns a non-2xx status code
- **THEN** the client logs the error and raises an exception that the ingestion service can catch

### Requirement: ReliefWeb normalizer maps reports to NormalizedRecord
The system SHALL normalize each ReliefWeb report record into a `NormalizedRecord` with these mappings:
- `title`: report title
- `body`: report body, summary, or excerpt in that priority order (first non-empty value)
- `url`: canonical ReliefWeb URL from the report's `href` or `url` field
- `published_at`: ReliefWeb publication date (`date.original` or equivalent)
- `latitude`: best available location centroid if present, otherwise NULL
- `longitude`: best available location centroid if present, otherwise NULL
- `event_type`: normalized internal EventType via deterministic mapping from report theme/disaster type
- `raw_metadata_json`: full ReliefWeb record fields including report `id` as `source_native_id`
- `embedding`, `sentiment_score`, `market_signal`: NULL

#### Scenario: Complete ReliefWeb report with body and location
- **WHEN** the normalizer receives a well-formed ReliefWeb report with body text and country location data
- **THEN** it returns a `NormalizedRecord` with the report title, body text, canonical URL, publication date, centroid coordinates, mapped event_type, and full raw metadata

#### Scenario: ReliefWeb report with summary but no body
- **WHEN** the normalizer receives a ReliefWeb report with no body but a summary field
- **THEN** it uses the summary as the `body` value

#### Scenario: ReliefWeb report with no location data
- **WHEN** the normalizer receives a ReliefWeb report with no country or location centroid
- **THEN** it returns a `NormalizedRecord` with `latitude=NULL` and `longitude=NULL`

#### Scenario: Malformed ReliefWeb report record
- **WHEN** the normalizer receives a ReliefWeb report missing critical fields (e.g., no id, no title)
- **THEN** it raises a normalization error that the ingestion service logs and skips

### Requirement: ReliefWeb event type mapping is deterministic
The system SHALL map ReliefWeb report themes and disaster types to internal `EventType` values using a static mapping dictionary. If the ReliefWeb category does not match any mapping key, the system SHALL default to `humanitarian_crisis`.

#### Scenario: Known ReliefWeb theme
- **WHEN** the normalizer receives a ReliefWeb report with theme "Flood"
- **THEN** it maps to `climate_disasters`

#### Scenario: Unknown ReliefWeb theme
- **WHEN** the normalizer receives a ReliefWeb report with an unrecognized theme
- **THEN** it maps to `humanitarian_crisis` as the default

### Requirement: ReliefWeb ingestion skips reports older than lookback window
The system SHALL discard any ReliefWeb report whose publication date is older than `INGESTION_LOOKBACK_DAYS` days from the current date, even if the API returns it.

#### Scenario: Report within lookback window
- **WHEN** a ReliefWeb report has publication date 5 days ago and lookback is 14 days
- **THEN** the report is processed and normalized

#### Scenario: Report outside lookback window
- **WHEN** a ReliefWeb report has publication date 18 days ago and lookback is 14 days
- **THEN** the report is discarded and not inserted

### Requirement: ReliefWeb manual trigger via FastAPI route
The system SHALL expose a `POST /ingestion/reliefweb` endpoint that triggers ReliefWeb ingestion and returns a structured `RunSummary` JSON response.

#### Scenario: Successful ReliefWeb ingestion via route
- **WHEN** a POST request is sent to `/ingestion/reliefweb`
- **THEN** the system runs the ReliefWeb ingestor and returns a RunSummary with source="reliefweb", counts for fetched/inserted/duplicates_skipped/malformed_skipped/db_failures, timestamps, and status

### Requirement: ReliefWeb manual trigger via CLI
The system SHALL support running `python -m app.ingestion.run_reliefweb` to execute ReliefWeb ingestion from the command line and print the RunSummary to stdout.

#### Scenario: CLI execution of ReliefWeb ingestor
- **WHEN** a developer runs `python -m app.ingestion.run_reliefweb` from the `backend/` directory
- **THEN** the ReliefWeb ingestor executes, prints the RunSummary JSON to stdout, and exits with code 0 on success or 1 on failure
