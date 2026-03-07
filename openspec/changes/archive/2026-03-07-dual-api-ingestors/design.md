## Context

The Global Event Intelligence platform currently serves events from a static mock repository (`MockEventRepository` backed by `seed_data.py`). The data models (`Source`, `ContentItem`, `EventType` enum) and read-only API routes (`/events`, `/filters`, `/timeline`) are already in place. The database schema defines `sources` and `content_table` (modeled as `ContentItem` in Pydantic) but no real database connection exists yet — all reads come from in-memory seed data.

This change introduces the first real data pipeline: two independent API ingestors that fetch recent records from ACLED and ReliefWeb, normalize them, and write them into PostgreSQL via `sources` and `content_table`. The existing read path is unaffected.

**Current state:**
- FastAPI app at `backend/app/main.py` with mock data
- Pydantic models in `backend/app/models/schemas.py` and `enums.py`
- No database driver, no real DB connection, no ingestion code
- `EventType` enum has 6 values; needs `humanitarian_crisis` added

**Constraints:**
- Ingestion-only — no embeddings, entity extraction, clustering, or graph population
- Manual trigger only — no scheduler, no frontend UI
- Must work locally against a dev `DATABASE_URL` and in production against AWS RDS PostgreSQL
- Each ingestor must be independently runnable and testable

## Goals / Non-Goals

**Goals:**
- Ingest ACLED events and ReliefWeb reports from the last 14 days into `content_table`
- Maintain two fully separate ingestor pipelines that share only infrastructure utilities
- Provide manual triggers via FastAPI dev routes and CLI entry points
- Idempotent ingestion with dedupe by source-native ID and URL
- Structured run summaries for every execution
- Add `raw_metadata_json JSONB` column for source-native metadata storage

**Non-Goals:**
- Embeddings generation during ingestion
- Entity extraction or NER
- Event clustering or `events` table population
- Graph relationship population (`event_relationships`, `content_entities`)
- Scheduled/cron execution
- Frontend ingestion UI or auth
- Updating existing rows on re-ingest (v1 is insert-or-skip)

## Decisions

### 1. Package layout: `app/ingestion/` with source-specific sub-packages

**Decision:** Create `backend/app/ingestion/` containing shared modules at the top level and source-specific modules in `acled/` and `reliefweb/` sub-packages.

```
app/ingestion/
├── __init__.py
├── config.py              # Shared env/config loading
├── db.py                  # Shared async DB connection pool
├── content_repository.py  # Shared insert/dedupe queries
├── dedupe_service.py      # Shared dedupe logic
├── ingestion_service.py   # Orchestrator (run one, run all)
├── models.py              # Ingestion-specific Pydantic models (RunSummary, NormalizedRecord)
├── run_all.py             # CLI: python -m app.ingestion.run_all
├── acled/
│   ├── __init__.py
│   ├── acled_client.py       # HTTP client for ACLED API
│   ├── acled_normalizer.py   # ACLED → NormalizedRecord mapping
│   └── run_acled.py          # CLI: python -m app.ingestion.run_acled (also __main__.py)
└── reliefweb/
    ├── __init__.py
    ├── reliefweb_client.py   # HTTP client for ReliefWeb API
    ├── reliefweb_normalizer.py  # ReliefWeb → NormalizedRecord mapping
    └── run_reliefweb.py      # CLI: python -m app.ingestion.run_reliefweb
```

**Rationale:** Sub-packages enforce the separation requirement at the file-system level. Shared modules are siblings, not parents, making dependency direction clear. Each `run_*.py` doubles as a CLI entry point (via `__main__.py` aliasing or direct module execution).

**Alternative considered:** Flat layout with all files in `app/ingestion/`. Rejected because it doesn't structurally enforce source separation and would become cluttered as more sources are added.

### 2. HTTP client: `httpx` (async)

**Decision:** Use `httpx.AsyncClient` for all API calls.

**Rationale:** Already widely adopted in the FastAPI ecosystem, supports async natively, has a clean API for timeout/retry configuration. The project has no existing HTTP client dependency, so there's no conflict.

**Alternative considered:** `aiohttp` — heavier dependency, less ergonomic for simple JSON API calls. `requests` — synchronous only, would block the event loop when called from FastAPI routes.

### 3. Database driver: `asyncpg` via raw SQL

**Decision:** Use `asyncpg` for PostgreSQL access with a connection pool. Write raw SQL for the small number of queries (insert content, check dedupe, ensure source rows).

**Rationale:** The ingestion layer has exactly 4-5 distinct queries. An ORM (SQLAlchemy) would add significant complexity and dependency weight for minimal benefit. `asyncpg` is the fastest Python PostgreSQL driver and works natively with `asyncio`.

**Alternative considered:** SQLAlchemy async with `asyncpg` backend — viable but over-engineered for the current query count. Can be adopted later if the query surface grows. `psycopg2` — synchronous, would require thread pool executor wrapping for FastAPI routes.

### 4. Normalization: intermediate `NormalizedRecord` Pydantic model

**Decision:** Both ingestors normalize source data into a shared `NormalizedRecord` Pydantic model before database insertion. This model mirrors `content_table` columns plus `raw_metadata_json`.

**Rationale:** Decouples source-specific parsing from database operations. The repository layer accepts `NormalizedRecord` instances and doesn't need to know which source produced them. Pydantic validation catches malformed records before DB writes.

**Alternative considered:** Direct dict-to-SQL mapping — loses validation, makes debugging harder, couples normalizers to DB schema.

### 5. Event type normalization: deterministic mapping dicts

**Decision:** Each normalizer contains a static `dict[str, EventType]` mapping source categories to internal event types. ACLED defaults to `geopolitics`; ReliefWeb defaults to `humanitarian_crisis`.

**Rationale:** Deterministic, testable, no ML dependency. Maps can be expanded without code changes beyond the dict.

### 6. Dedupe strategy: check-before-insert with source-native ID and URL

**Decision:** Before inserting, query `content_table` for existing rows matching (source_id + native_id via `raw_metadata_json->>'source_native_id'`) or (source_id + url). Skip if found.

**Rationale:** Simple, idempotent, no upsert complexity. The `raw_metadata_json` column stores the source-native ID, enabling future index creation for fast lookups.

**Alternative considered:** `INSERT ... ON CONFLICT DO NOTHING` with a unique constraint — cleaner SQL but requires schema migration to add the constraint. Can be done in a follow-up.

### 7. FastAPI routes: separate ingestion router

**Decision:** Add `app/routers/ingestion.py` with three `POST` endpoints under `/ingestion/` prefix. No auth in v1.

**Rationale:** Keeps ingestion routes isolated from the existing read-only event routes. The router is included in `main.py` alongside existing routers.

### 8. Run summary: consistent JSON shape from all entry points

**Decision:** Every run (single source or run-all) returns a `RunSummary` Pydantic model serialized to JSON. `run_all` returns a wrapper with individual summaries and an aggregate status.

**Rationale:** Enables programmatic consumption from both CLI (printed to stdout) and API routes (returned as response body).

### 9. Connection management for CLI vs server

**Decision:** `db.py` exposes `get_pool()` which lazily creates an `asyncpg` connection pool. CLI entry points create and close the pool explicitly. FastAPI routes use a lifespan-managed pool.

**Rationale:** Avoids pool leaks in CLI mode while reusing the pool across requests in server mode.

## Risks / Trade-offs

- **ACLED API rate limits or auth changes** → Mitigation: configurable timeout and retry with exponential backoff in `acled_client.py`; API token loaded from env var.
- **ReliefWeb appname rejection** → Mitigation: `RELIEFWEB_APPNAME` env var is required; clear error message if missing or rejected.
- **No unique constraint for dedupe** → Mitigation: application-level check-before-insert is sufficient for manual-trigger-only v1 with low concurrency. Add DB constraint in follow-up.
- **Large result sets from 14-day window** → Mitigation: both APIs support pagination; clients implement paginated fetching with configurable page size.
- **No connection pooling tuning** → Mitigation: `asyncpg` pool with sensible defaults (min=2, max=10) is adequate for manual trigger workload.
- **`raw_metadata_json` column requires schema migration** → Mitigation: provide a SQL migration file and document the `ALTER TABLE` step. Column is nullable so existing rows are unaffected.
