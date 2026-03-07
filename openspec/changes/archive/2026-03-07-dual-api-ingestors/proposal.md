## Why

The platform currently serves global events from static seed data via a mock repository. To deliver real intelligence, the backend needs to ingest live data from authoritative open sources. ACLED and ReliefWeb are the two highest-value, API-accessible sources for geopolitical events and humanitarian reports respectively. Building ingestion now unblocks all downstream features (embeddings, clustering, entity extraction) without coupling to them.

## What Changes

- Add an `app/ingestion/` package with two independent API ingestors (ACLED, ReliefWeb)
- Add shared ingestion infrastructure: database access (`db.py`), config loading (`config.py`), content repository (`content_repository.py`), dedupe service (`dedupe_service.py`), ingestion orchestrator (`ingestion_service.py`)
- Add `raw_metadata_json JSONB` column to `content_table` for storing source-native IDs, raw taxonomy, and ingest diagnostics
- Add `humanitarian_crisis` to the `EventType` enum (required by the normalization spec but missing from current enum)
- Add three FastAPI dev-only routes: `POST /ingestion/acled`, `POST /ingestion/reliefweb`, `POST /ingestion/run-all`
- Add three CLI entry points: `python -m app.ingestion.run_acled`, `run_reliefweb`, `run_all`
- Add new dependencies: `httpx`, `asyncpg` (or `psycopg2-binary`), `python-dotenv`
- Add environment variables: `DATABASE_URL`, `ACLED_API_TOKEN`, `RELIEFWEB_APPNAME`, `INGESTION_LOOKBACK_DAYS`
- Ensure `sources` table rows for ACLED (trust 0.90) and ReliefWeb (trust 0.88) exist
- Populate only `sources` and `content_table`; no embeddings, entities, events, or relationships

## Capabilities

### New Capabilities
- `acled-ingestion`: ACLED API client, event normalization, event-type mapping, and manual trigger (route + CLI)
- `reliefweb-ingestion`: ReliefWeb Reports API client, report normalization, event-type mapping, and manual trigger (route + CLI)
- `ingestion-infrastructure`: Shared DB access, config, content repository, dedupe service, ingestion orchestrator, run-all coordination, and structured run summaries

### Modified Capabilities

## Impact

- **Backend code**: New `app/ingestion/` package (~12 modules), new ingestion router, enum addition
- **Database schema**: `raw_metadata_json` column added to `content_table`; `sources` seeded with two rows
- **Dependencies**: `httpx`, database driver, `python-dotenv` added to `requirements.txt`
- **Environment**: Four new env vars required for operation
- **Existing features**: No breaking changes; existing mock-based read paths are unaffected
