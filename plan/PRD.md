# Argus — Product Requirements Document

## Vision

Argus is a 3D global event intelligence platform that aggregates world events daily, stores them in a semantically searchable database, and visualizes them on an interactive globe. Users can explore events spatially and temporally, query an AI agent for analysis, and discover connections between events through graph-based relationships.

The platform is source-agnostic — while the hackathon prototype focused on Canada-impact framing, the production system should support any analytical lens or persona.

## Current State (MVP)

Working prototype with:
- 3D globe rendering events as points with similarity arcs
- AI agent (Graph-RAG) with persona-aware Gemini synthesis
- Hackathon-era scrapers for GDELT, ACLED, Polymarket, Kalshi (will not be used directly — new scrapers will be written, but these serve as reference)
- PostgreSQL + pgvector for semantic search
- Client-side filtering and timeline scrubbing

Key gaps: no deployment config, no scheduled scraping, no caching, no tests, high AI token costs, dead code from hackathon iteration, legacy Cloudinary/S3 media code that is no longer needed. Existing scrapers need to be replaced with new, production-grade implementations — the current ones are MVP-quality reference code only.

## Team & Constraints

- 4 people, part-time
- Low budget — minimize per-request AI spend
- Target: production-deployable within ~7 weeks (4 phases)

---

## Phase 1: Foundation (Week 1–2)

**Goal:** Make the app deployable and the codebase clean enough to work on confidently.

### 1.1 Containerization

| # | Ticket | Priority |
|---|--------|----------|
| 1 | Create backend Dockerfile (FastAPI + uvicorn, multi-stage build) | P0 |
| 2 | Create frontend Dockerfile (Vite build -> nginx static serve) | P0 |
| 3 | Create `docker-compose.yml` with services: backend, frontend, postgres+pgvector, redis | P0 |
| 4 | Add `.dockerignore` files (exclude `.env`, `node_modules`, `.venv`, `__pycache__`) | P0 |

### 1.2 CI/CD

| # | Ticket | Priority |
|---|--------|----------|
| 5 | Set up GitHub Actions CI: ruff lint/format, TypeScript typecheck, docker build | P0 |
| 6 | Set up GitHub Actions CD: build images, push to registry, deploy to hosting | P1 |
| 7 | Choose hosting provider (Railway, Fly.io, or small VPS) and document deploy process | P1 |

### 1.3 Dead Code Removal

| # | Ticket | Priority |
|---|--------|----------|
| 8 | Delete junk scrapers: `eonet.py`, `eonet_db.py`, `social_scraper.py`, `reddit.py`, `reddit_classifier.py`, `reddit_db.py`, `reddit_schema.sql`, `Reddit Scraper/`, `natural-disasters/`, `ryan_scrapers/` | P0 |
| 9 | Move remaining hackathon scrapers (`gdelt.py`, `kalshi.py`, `polymarket.py`, `acled/`) into a `scrapers/_reference/` directory — these won't be used directly but are kept as design inspiration (see "Scraper Reference Guide" below) | P0 |
| 10 | Remove duplicate `content_repository.py` (exists in both `repositories/` and `ingestion/`) — consolidate into one | P0 |
| 11 | Remove all Cloudinary and S3 media code — no longer needed. Delete `utils/mediaConfig.ts`, remove `@cloudinary/react` and `@cloudinary/url-gen` deps from frontend, remove `cloudinary` and `boto3` deps from backend, drop `image_url` and `s3_url` columns from `content_table`, remove all `CLOUDINARY_*` and `AWS_*`/`S3_*` env vars | P0 |
| 12 | Audit and remove any other dead imports, unused functions, or commented-out code | P1 |

### 1.4 Security Baseline

| # | Ticket | Priority |
|---|--------|----------|
| 13 | Lock down CORS origins — remove `*` wildcard, use env-configured allowed origins | P0 |
| 14 | Add rate limiting middleware on `/agent/query` and `/content/{id}/realtime-analysis` (these burn AI tokens) | P0 |
| 15 | Validate all secrets are loaded from env vars; fail fast on startup if required vars missing | P0 |

---

## Phase 2: Automation & Cost Optimization (Week 2–3)

**Goal:** Automate daily data ingestion and drastically cut AI token spend.

### 2.1 Scheduled Scraping

| # | Ticket | Priority |
|---|--------|----------|
| 16 | Design `BaseScraper` ABC interface: `async fetch() -> list[NormalizedRow]` with built-in rate limiting, error handling, and dedup. Use `kalshi.py` rate limiter and `ingestion_service.py` error patterns as reference. | P0 |
| 17 | Write new production scrapers implementing `BaseScraper` for each data source (determine which sources to keep/add based on product needs) | P0 |
| 18 | Create unified scrape entrypoint (`run_daily_pipeline.py`) that runs all scrapers + embedding backfill in sequence | P0 |
| 19 | Add cron scheduler (APScheduler in a separate container, or cron in docker-compose) | P0 |
| 20 | Define scraping schedule (e.g. 1x/day, 2x/day per source) | P0 |
| 21 | Add `scrape_runs` logging table (source, status, rows_inserted, errors, duration_ms, started_at) | P1 |
| 22 | Add idempotency guards — URL-based dedup check before insert, not after | P0 |
| 23 | Add failure alerting (Discord webhook or email on scrape errors) | P2 |

### 2.2 Embedding Cost Reduction

| # | Ticket | Priority |
|---|--------|----------|
| 24 | **Switch embeddings to local model** — replace OpenAI `text-embedding-3-small` with `sentence-transformers` (e.g. `all-MiniLM-L6-v2`, 384 dims). Run locally in backend container. Update vector column dimension and include a one-time re-embedding migration/rollout plan (1536 -> 384) to avoid query downtime. | P0 |
| 25 | Batch embedding generation — process 100+ items per batch instead of one-at-a-time | P0 |
| 26 | Deduplicate content before generating embeddings (currently embeddings are generated before dedup) | P1 |

### 2.3 AI Response Caching (Redis)

| # | Ticket | Priority |
|---|--------|----------|
| 27 | Add Redis client utility module with connection pooling | P0 |
| 28 | Cache `/content/points` response — invalidate on new scrape run completion | P0 |
| 29 | Cache `/content/arcs` response per threshold value (TTL = until next scrape) | P1 |
| 30 | Cache Gemini confidence scores per content_id (TTL = 24h) | P0 |
| 31 | Cache Gemini realtime analysis per `(content_id, user_role)` (TTL = 6h) | P0 |
| 32 | Cache agent query results keyed on `(normalized_query_hash, persona)` (TTL = 1h) | P1 |

### 2.4 Additional Cost Controls

| # | Ticket | Priority |
|---|--------|----------|
| 33 | Add token usage tracking — log Gemini and OpenAI (if still used) token counts per call to a `token_usage` table | P1 |
| 34 | Pre-compute confidence scores during scrape pipeline instead of on-demand per user click | P2 |
| 35 | Replace per-request Google Search grounding with daily cached news summaries scraped during pipeline | P2 |

---

## Phase 3: Schema & Code Quality (Week 3–5)

**Goal:** Clean up the data model, modularize backend code, add test coverage.

### 3.1 Database Schema Improvements

| # | Ticket | Priority |
|---|--------|----------|
| 36 | Set up Alembic for migration management (replace raw SQL files) | P0 |
| 37 | Rename `content_table` -> `articles` | P1 |
| 38 | Split AI-generated fields into `article_analysis` table (embedding, sentiment_score, market_signal, confidence_score) | P1 |
| 39 | Add `scrape_source` enum column to replace generic FK to `sources` table | P2 |
| 40 | Add composite index on `(event_type, published_at)` for filtered timeline queries | P1 |
| 41 | Add `last_scraped_at` column to sources for freshness tracking | P2 |
| 42 | Clean up unused columns and tables from hackathon iteration (including dropped `image_url`, `s3_url`) | P1 |

### 3.2 Backend Modularization

| # | Ticket | Priority |
|---|--------|----------|
| 43 | Create shared `db.py` module — single asyncpg pool used by all services (currently duplicated in `ingestion/db.py` and inline connects) | P0 |
| 44 | Consolidate all Pydantic models into a single `schemas/` package | P1 |
| 45 | Replace all `print()` statements with structured `logging` (use correlation IDs per request) | P1 |
| 46 | Add input validation on all API endpoints (query length limits, coordinate bounds, UUID format) | P1 |

### 3.3 Testing

| # | Ticket | Priority |
|---|--------|----------|
| 47 | Set up pytest with async fixtures (asyncpg test DB, httpx AsyncClient) | P0 |
| 48 | Write tests for new scraper implementations and row normalization | P0 |
| 49 | Write tests for deduplication logic | P1 |
| 50 | Write tests for agent query classification (`_classify_query`) | P1 |
| 51 | Write API integration tests for `/content/points`, `/agent/query` | P1 |
| 52 | Add frontend smoke tests (Vitest + React Testing Library) for Globe render, Agent query flow | P2 |
| 53 | Add pre-commit hooks: ruff lint+format, TypeScript typecheck | P0 |

---

## Phase 4: Frontend Polish & Observability (Week 5–7)

**Goal:** Make the UI production-grade and add operational visibility.

### 4.1 Frontend UX

| # | Ticket | Priority |
|---|--------|----------|
| 54 | Add loading skeleton/spinner on initial data fetch | P0 |
| 55 | Lazy-load Globe component (three.js is ~500KB) with React.lazy + Suspense | P1 |
| 56 | Add error boundaries around Globe, Agent, and Modal components | P0 |
| 57 | Memoize expensive computations (arc filtering, point color mapping) with useMemo/useCallback | P1 |
| 58 | Add responsive layout — mobile/tablet support or graceful "desktop-only" message | P1 |
| 59 | Add URL-based routing (React Router) for shareable/bookmarkable globe state | P2 |
| 60 | Add "no results" empty states for agent queries and empty filtered views | P1 |
| 61 | Move inline styles and magic numbers to shared constants / design tokens | P2 |

### 4.2 Observability

| # | Ticket | Priority |
|---|--------|----------|
| 62 | Add structured logging with request correlation IDs (middleware) | P1 |
| 63 | Add simple admin dashboard page: scrape history, DB row counts, token spend summary | P2 |
| 64 | Add uptime monitoring on `/health` endpoint (UptimeRobot free tier or similar) | P1 |

### 4.3 Security Hardening

| # | Ticket | Priority |
|---|--------|----------|
| 65 | Audit all raw SQL for injection risks — parameterize any string-interpolated queries | P0 |
| 66 | Add API key or lightweight session auth for agent/analysis endpoints | P1 |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Daily scraping runs automatically | Yes, with logged success/failure |
| Embedding cost per scrape cycle | < $0.01 (local model) |
| Gemini API calls per unique user action | Max 1 (cached thereafter) |
| Time to deploy from commit | < 10 minutes |
| Backend test coverage on critical paths | > 70% |
| Frontend initial load time | < 3 seconds (gzipped, lazy-loaded) |
| Uptime | > 99% (monitored) |

---

## Scraper Reference Guide

The existing hackathon scrapers will **not** be used directly in production. They are moved to `scrapers/_reference/` as design inspiration. New scrapers should be written from scratch implementing the `BaseScraper` ABC (ticket #16).

### Which reference files to study, and why

| File | Quality | What to learn from it |
|------|---------|----------------------|
| `kalshi.py` | Excellent | Async rate limiter class (`_RateLimiter` with lock-based queueing, 10 req/sec), cursor-based pagination, `asyncio.gather` with `return_exceptions=True` |
| `gdelt.py` | Excellent | Dual-path fetch (BigQuery primary, DOC API fallback), complex event-type mapping via CAMEO codes, Goldstein scale normalization, title synthesis from multiple fields |
| `row_format.py` | Excellent | Schema-aligned output contract — keyword-only args prevent mistakes. **Copy this pattern into all new scrapers.** |
| `acled_normalizer.py` | Good | Clean normalizer pattern: type-safe `NormalizedRecord` return, graceful fallback for every nullable field |
| `ingestion_service.py` | Good | Per-record error handling with `RunSummary` tracking (malformed, duplicates, db_failures), dedup integration |
| `polymarket.py` | Decent | Simplest example — good starting point for straightforward REST APIs, tag-based filtering |
| `scraping_service.py` | Decent | Orchestration pattern: per-scraper try-catch, error records appended (visibility over silent failures) |

### Patterns to carry forward into new scrapers

1. **Separate fetch from normalization** — client fetches raw data, normalizer produces `NormalizedRow`
2. **Use async rate limiters, not `time.sleep()`** — see `kalshi.py`'s `_RateLimiter` class
3. **All output goes through `row_format.make_content_row()`** — enforces schema contract
4. **Per-record error handling** — one bad record shouldn't abort the batch
5. **Track stats** — count inserted, skipped, failed per run for observability
6. **Dedup before embedding** — check URL uniqueness before generating expensive vectors

---

## Non-Goals (for now)

- Mobile app (web-only is fine)
- User accounts / auth (public dashboard for now, API key auth only)
- Real-time websocket streaming (polling/refresh is sufficient)
- Multi-language support
- Custom event submission by users
