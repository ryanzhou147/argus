## ADDED Requirements

### Requirement: Ingestion config loads environment variables
The system SHALL provide a config module that loads and validates these environment variables:
- `DATABASE_URL` (required): PostgreSQL connection string
- `ACLED_API_TOKEN` (required for ACLED runs): ACLED API authentication token
- `RELIEFWEB_APPNAME` (required for ReliefWeb runs): pre-approved ReliefWeb application name
- `INGESTION_LOOKBACK_DAYS` (optional, default 14): number of days to look back

#### Scenario: All environment variables present
- **WHEN** config is loaded with all required env vars set
- **THEN** the config object exposes all values with correct types (int for lookback_days)

#### Scenario: DATABASE_URL missing
- **WHEN** config is loaded without `DATABASE_URL`
- **THEN** a configuration error is raised with a message indicating the missing variable

#### Scenario: INGESTION_LOOKBACK_DAYS not set
- **WHEN** config is loaded without `INGESTION_LOOKBACK_DAYS`
- **THEN** the config defaults to 14 days

### Requirement: Database module provides async connection pool
The system SHALL provide a database module that creates and manages an `asyncpg` connection pool using `DATABASE_URL`. The pool SHALL be lazily initialized and provide explicit open/close lifecycle methods for both CLI and server usage.

#### Scenario: Pool initialization for CLI
- **WHEN** a CLI entry point calls `get_pool()`
- **THEN** an asyncpg connection pool is created and returned, and the CLI explicitly closes it on exit

#### Scenario: Pool initialization for FastAPI
- **WHEN** the FastAPI app starts
- **THEN** the pool is created during app lifespan startup and closed during shutdown

#### Scenario: DATABASE_URL is invalid
- **WHEN** the pool is initialized with an invalid `DATABASE_URL`
- **THEN** a connection error is raised with a descriptive message

### Requirement: Content repository inserts normalized records
The system SHALL provide a content repository module with an `insert_content` method that accepts a `NormalizedRecord` and inserts it into `content_table`. The insert SHALL include all mapped fields plus `raw_metadata_json` and `created_at` (set to current timestamp).

#### Scenario: Successful insert of a normalized record
- **WHEN** `insert_content` is called with a valid `NormalizedRecord`
- **THEN** a new row is inserted into `content_table` with all fields mapped correctly and `created_at` set to the current timestamp

#### Scenario: Database write failure
- **WHEN** `insert_content` encounters a database error
- **THEN** the error is raised so the ingestion service can log it, increment `db_failures`, and continue with the next record

### Requirement: Content repository ensures source rows exist
The system SHALL provide a method to ensure that the `sources` table contains rows for ACLED and ReliefWeb with the specified attributes:
- ACLED: name="ACLED", type="api", base_url=ACLED API base URL, trust_score=0.90
- ReliefWeb: name="ReliefWeb", type="api", base_url=ReliefWeb API base URL, trust_score=0.88

#### Scenario: Sources do not exist yet
- **WHEN** `ensure_sources` is called and no ACLED or ReliefWeb rows exist in `sources`
- **THEN** both rows are inserted with the correct attributes

#### Scenario: Sources already exist
- **WHEN** `ensure_sources` is called and both source rows already exist
- **THEN** no duplicate rows are created (idempotent)

### Requirement: Dedupe service checks for duplicate records
The system SHALL provide a dedupe service that checks whether a record already exists in `content_table` before insertion. Dedupe checks SHALL be performed in this order:
1. If source-native ID exists in `raw_metadata_json`, check by `source_id` + `source_native_id` in `raw_metadata_json`
2. Check by `source_id` + `url`
If either check finds a match, the record is considered a duplicate.

#### Scenario: Record with matching source-native ID exists
- **WHEN** dedupe is checked for a record whose source_native_id already exists for the same source_id
- **THEN** the dedupe service returns `True` (is duplicate)

#### Scenario: Record with matching URL exists
- **WHEN** dedupe is checked for a record whose URL already exists for the same source_id
- **THEN** the dedupe service returns `True` (is duplicate)

#### Scenario: Record is new
- **WHEN** dedupe is checked for a record with no matching source_native_id or URL
- **THEN** the dedupe service returns `False` (not duplicate)

### Requirement: Ingestion service orchestrates single-source runs
The system SHALL provide an ingestion service that orchestrates a single-source ingestion run. For each run, it SHALL:
1. Ensure source row exists
2. Fetch records via the source client
3. Normalize each record, skipping malformed ones
4. Check dedupe for each record, skipping duplicates
5. Insert non-duplicate records, logging DB failures
6. Return a `RunSummary` with all counts and timestamps

#### Scenario: Successful single-source ingestion
- **WHEN** the ingestion service runs for ACLED with 50 fetched records, 5 duplicates, 2 malformed
- **THEN** it returns a RunSummary with fetched=50, inserted=43, duplicates_skipped=5, malformed_skipped=2, db_failures=0, status="success"

#### Scenario: All records are duplicates
- **WHEN** the ingestion service runs and every record is a duplicate
- **THEN** it returns a RunSummary with inserted=0, duplicates_skipped=N, status="success"

#### Scenario: Database failure on some records
- **WHEN** the ingestion service encounters DB write failures on 3 records out of 50
- **THEN** it continues processing remaining records and returns RunSummary with db_failures=3, status="success" (partial DB failures don't change overall status)

### Requirement: Run-all executes both ingestors independently
The system SHALL provide a `run_all` function that executes both ACLED and ReliefWeb ingestors independently. The result of one ingestor SHALL NOT affect whether the other runs.

#### Scenario: Both ingestors succeed
- **WHEN** `run_all` is executed and both ACLED and ReliefWeb complete successfully
- **THEN** it returns status="success" with individual RunSummaries for each source

#### Scenario: One ingestor fails
- **WHEN** `run_all` is executed and ACLED fails but ReliefWeb succeeds
- **THEN** it returns status="partial_success" with ACLED's failure summary and ReliefWeb's success summary

#### Scenario: Both ingestors fail
- **WHEN** `run_all` is executed and both ACLED and ReliefWeb fail
- **THEN** it returns status="failure" with both failure summaries

### Requirement: Run-all FastAPI route
The system SHALL expose a `POST /ingestion/run-all` endpoint that triggers both ingestors and returns the combined run result.

#### Scenario: Run-all via API
- **WHEN** a POST request is sent to `/ingestion/run-all`
- **THEN** both ingestors execute independently and the response contains individual summaries and aggregate status

### Requirement: Run-all CLI entry point
The system SHALL support running `python -m app.ingestion.run_all` to execute both ingestors from the command line.

#### Scenario: CLI execution of run-all
- **WHEN** a developer runs `python -m app.ingestion.run_all` from the `backend/` directory
- **THEN** both ingestors execute, the combined RunSummary is printed to stdout, and the exit code is 0 for success, 1 for failure, 0 for partial_success

### Requirement: RunSummary has consistent shape
Every ingestion run SHALL return a `RunSummary` with this shape:
- `source`: "acled" | "reliefweb" | "all"
- `lookback_days`: integer
- `fetched`: integer
- `inserted`: integer
- `duplicates_skipped`: integer
- `malformed_skipped`: integer
- `db_failures`: integer
- `started_at`: ISO timestamp
- `finished_at`: ISO timestamp
- `status`: "success" | "partial_success" | "failure"

#### Scenario: RunSummary from successful ACLED run
- **WHEN** an ACLED ingestion completes with 30 fetched, 25 inserted, 3 duplicates, 2 malformed
- **THEN** the RunSummary contains source="acled", lookback_days=14, fetched=30, inserted=25, duplicates_skipped=3, malformed_skipped=2, db_failures=0, status="success", and valid timestamps

### Requirement: Schema includes raw_metadata_json column
The `content_table` schema SHALL include a `raw_metadata_json JSONB` column that stores:
- `source_native_id`: the source-specific unique identifier
- Raw source taxonomy fields
- Source-specific metadata
- Ingest diagnostics (e.g., normalization warnings)

The column SHALL be nullable to maintain backward compatibility with existing rows.

#### Scenario: Record inserted with raw metadata
- **WHEN** a normalized record is inserted into content_table
- **THEN** the `raw_metadata_json` column contains the source-native ID, raw taxonomy, and any ingest diagnostics as a JSON object

### Requirement: EventType enum includes humanitarian_crisis
The `EventType` enum SHALL include `humanitarian_crisis` as a valid value, in addition to the existing six values.

#### Scenario: humanitarian_crisis is a valid event type
- **WHEN** a normalized record has event_type="humanitarian_crisis"
- **THEN** the record is accepted by validation and inserted without error
