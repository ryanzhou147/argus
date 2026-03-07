## 1. Foundation: Dependencies, Config, and Enum Update

- [x] 1.1 Add `httpx`, `asyncpg`, `python-dotenv` to `backend/requirements.txt`
- [x] 1.2 Add `humanitarian_crisis` value to `EventType` enum in `backend/app/models/enums.py`
- [x] 1.3 Create `backend/app/ingestion/__init__.py`
- [x] 1.4 Create `backend/app/ingestion/config.py` — load and validate `DATABASE_URL`, `ACLED_API_TOKEN`, `RELIEFWEB_APPNAME`, `INGESTION_LOOKBACK_DAYS` (default 14)
- [x] 1.5 Create `backend/app/ingestion/models.py` — define `NormalizedRecord` and `RunSummary` Pydantic models

## 2. Database Layer

- [x] 2.1 Create `backend/app/ingestion/db.py` — async connection pool via `asyncpg` with lazy init, explicit open/close, `get_pool()` accessor
- [x] 2.2 Create SQL migration file `backend/migrations/001_add_raw_metadata_json.sql` — `ALTER TABLE content_table ADD COLUMN raw_metadata_json JSONB`
- [x] 2.3 Create `backend/app/ingestion/content_repository.py` — `insert_content(pool, record)` and `ensure_sources(pool)` methods with raw SQL
- [x] 2.4 Create `backend/app/ingestion/dedupe_service.py` — `is_duplicate(pool, source_id, native_id, url)` checking by source_native_id in raw_metadata_json then by URL

## 3. ACLED Ingestor

- [x] 3.1 Create `backend/app/ingestion/acled/__init__.py`
- [x] 3.2 Create `backend/app/ingestion/acled/acled_client.py` — async HTTP client that fetches paginated ACLED events for the last N days using `ACLED_API_TOKEN`
- [x] 3.3 Create `backend/app/ingestion/acled/acled_normalizer.py` — normalize ACLED events to `NormalizedRecord` with deterministic title synthesis, event type mapping (default: `geopolitics`), and `raw_metadata_json` population
- [x] 3.4 Create `backend/app/ingestion/acled/run_acled.py` — CLI entry point (`python -m app.ingestion.acled.run_acled`) that runs ACLED ingestion and prints RunSummary

## 4. ReliefWeb Ingestor

- [x] 4.1 Create `backend/app/ingestion/reliefweb/__init__.py`
- [x] 4.2 Create `backend/app/ingestion/reliefweb/reliefweb_client.py` — async HTTP client that fetches paginated ReliefWeb reports for the last N days using `RELIEFWEB_APPNAME`
- [x] 4.3 Create `backend/app/ingestion/reliefweb/reliefweb_normalizer.py` — normalize ReliefWeb reports to `NormalizedRecord` with body/summary/excerpt fallback, event type mapping (default: `humanitarian_crisis`), location centroid extraction, and `raw_metadata_json` population
- [x] 4.4 Create `backend/app/ingestion/reliefweb/run_reliefweb.py` — CLI entry point (`python -m app.ingestion.reliefweb.run_reliefweb`) that runs ReliefWeb ingestion and prints RunSummary

## 5. Ingestion Orchestrator

- [x] 5.1 Create `backend/app/ingestion/ingestion_service.py` — `run_source(source_name, client, normalizer)` orchestrator: ensure source → fetch → normalize → dedupe → insert → return RunSummary; plus `run_all()` with independent execution and aggregate status
- [x] 5.2 Create `backend/app/ingestion/run_all.py` — CLI entry point (`python -m app.ingestion.run_all`) that runs both ingestors and prints combined result

## 6. FastAPI Routes

- [x] 6.1 Create `backend/app/routers/ingestion.py` — three POST routes: `/ingestion/acled`, `/ingestion/reliefweb`, `/ingestion/run-all`
- [x] 6.2 Register ingestion router in `backend/app/main.py`

## 7. Verification

- [x] 7.1 Verify `python -m app.ingestion.acled.run_acled` runs without crash (with valid env vars or graceful config error)
- [x] 7.2 Verify `python -m app.ingestion.reliefweb.run_reliefweb` runs without crash
- [x] 7.3 Verify `python -m app.ingestion.run_all` runs without crash
- [x] 7.4 Verify FastAPI app starts with ingestion routes registered (`/ingestion/acled`, `/ingestion/reliefweb`, `/ingestion/run-all` appear in docs)
- [x] 7.5 Verify ACLED normalizer maps known event types correctly and defaults unknown to `geopolitics`
- [x] 7.6 Verify ReliefWeb normalizer maps known themes correctly and defaults unknown to `humanitarian_crisis`
- [x] 7.7 Verify dedupe service correctly identifies duplicates by source_native_id and by URL
