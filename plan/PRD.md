# Argus — Product Requirements Document

## Vision

Argus is a 3D global event intelligence platform that aggregates world events daily, stores them in a semantically searchable database, and visualizes them on an interactive globe. Users can explore events spatially and temporally, query an AI agent for analysis, and discover connections between events through graph-based relationships.

The platform is source-agnostic — while the hackathon prototype focused on Canada-impact framing, the production system should support any analytical lens or persona.

## Current State (MVP)

Working prototype with:
- 3D globe rendering events as points with similarity arcs
- AI agent (Graph-RAG) with persona-aware Gemini synthesis
- Scrapers for GDELT, ACLED, Polymarket, Kalshi
- PostgreSQL + pgvector for semantic search
- Client-side filtering and timeline scrubbing

Key gaps: no deployment config, no scheduled scraping, no caching, no tests, high AI token costs, dead code from hackathon iteration.

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
| 8 | Delete unused scrapers: `eonet.py`, `eonet_db.py`, `social_scraper.py`, `reddit.py`, `reddit_classifier.py`, `reddit_db.py`, `Reddit Scraper/`, `natural-disasters/`, `ryan_scrapers/` | P0 |
| 9 | Remove duplicate `content_repository.py` (exists in both `repositories/` and `ingestion/`) — consolidate into one | P0 |
| 10 | Audit and remove any other dead imports, unused functions, or commented-out code | P1 |

### 1.4 Security Baseline

| # | Ticket | Priority |
|---|--------|----------|
| 11 | Lock down CORS origins — remove `*` wildcard, use env-configured allowed origins | P0 |
| 12 | Add rate limiting middleware on `/agent/query` and `/content/{id}/realtime-analysis` (these burn AI tokens) | P0 |
| 13 | Validate all secrets are loaded from env vars; fail fast on startup if required vars missing | P0 |

---

## Phase 2: Automation & Cost Optimization (Week 2–3)

**Goal:** Automate daily data ingestion and drastically cut AI token spend.

### 2.1 Scheduled Scraping

| # | Ticket | Priority |
|---|--------|----------|
| 14 | Create unified scrape entrypoint (`run_daily_pipeline.py`) that runs all scrapers + embedding backfill in sequence | P0 |
| 15 | Add cron scheduler (APScheduler in a separate container, or cron in docker-compose) | P0 |
| 16 | Define scraping schedule: GDELT 1x/day, ACLED 1x/day, Polymarket+Kalshi 2x/day | P0 |
| 17 | Add `scrape_runs` logging table (source, status, rows_inserted, errors, duration_ms, started_at) | P1 |
| 18 | Add idempotency guards — URL-based dedup check before insert, not after | P0 |
| 19 | Add failure alerting (Discord webhook or email on scrape errors) | P2 |

### 2.2 Embedding Cost Reduction

| # | Ticket | Priority |
|---|--------|----------|
| 20 | **Switch embeddings to local model** — replace OpenAI `text-embedding-3-small` with `sentence-transformers` (e.g. `all-MiniLM-L6-v2`, 384 dims). Run locally in backend container. Update vector column dimension. | P0 |
| 21 | Batch embedding generation — process 100+ items per batch instead of one-at-a-time | P0 |
| 22 | Deduplicate content before generating embeddings (currently embeddings are generated before dedup) | P1 |

### 2.3 AI Response Caching (Redis)

| # | Ticket | Priority |
|---|--------|----------|
| 23 | Add Redis client utility module with connection pooling | P0 |
| 24 | Cache `/content/points` response — invalidate on new scrape run completion | P0 |
| 25 | Cache `/content/arcs` response per threshold value (TTL = until next scrape) | P1 |
| 26 | Cache Gemini confidence scores per content_id (TTL = 24h) | P0 |
| 27 | Cache Gemini realtime analysis per `(content_id, user_role)` (TTL = 6h) | P0 |
| 28 | Cache agent query results keyed on `(normalized_query_hash, persona)` (TTL = 1h) | P1 |

### 2.4 Additional Cost Controls

| # | Ticket | Priority |
|---|--------|----------|
| 29 | Add token usage tracking — log Gemini and OpenAI (if still used) token counts per call to a `token_usage` table | P1 |
| 30 | Pre-compute confidence scores during scrape pipeline instead of on-demand per user click | P2 |
| 31 | Replace per-request Google Search grounding with daily cached news summaries scraped during pipeline | P2 |

---

## Phase 3: Schema & Code Quality (Week 3–5)

**Goal:** Clean up the data model, modularize backend code, add test coverage.

### 3.1 Database Schema Improvements

| # | Ticket | Priority |
|---|--------|----------|
| 32 | Set up Alembic for migration management (replace raw SQL files) | P0 |
| 33 | Rename `content_table` -> `articles` | P1 |
| 34 | Split AI-generated fields into `article_analysis` table (embedding, sentiment_score, market_signal, confidence_score) | P1 |
| 35 | Add `scrape_source` enum column to replace generic FK to `sources` table | P2 |
| 36 | Add composite index on `(event_type, published_at)` for filtered timeline queries | P1 |
| 37 | Add `last_scraped_at` column to sources for freshness tracking | P2 |
| 38 | Clean up unused columns and tables from hackathon iteration | P1 |

### 3.2 Backend Modularization

| # | Ticket | Priority |
|---|--------|----------|
| 39 | Create shared `db.py` module — single asyncpg pool used by all services (currently duplicated in `ingestion/db.py` and inline connects) | P0 |
| 40 | Extract `BaseScraper` ABC interface: `async fetch() -> list[NormalizedRow]`. Make GDELT, ACLED, Polymarket, Kalshi implement it. | P1 |
| 41 | Consolidate all Pydantic models into a single `schemas/` package | P1 |
| 42 | Replace all `print()` statements with structured `logging` (use correlation IDs per request) | P1 |
| 43 | Add input validation on all API endpoints (query length limits, coordinate bounds, UUID format) | P1 |

### 3.3 Testing

| # | Ticket | Priority |
|---|--------|----------|
| 44 | Set up pytest with async fixtures (asyncpg test DB, httpx AsyncClient) | P0 |
| 45 | Write tests for scraper row normalization (`row_format.py`, ACLED normalizer) | P0 |
| 46 | Write tests for deduplication logic | P1 |
| 47 | Write tests for agent query classification (`_classify_query`) | P1 |
| 48 | Write API integration tests for `/content/points`, `/agent/query` | P1 |
| 49 | Add frontend smoke tests (Vitest + React Testing Library) for Globe render, Agent query flow | P2 |
| 50 | Add pre-commit hooks: ruff lint+format, TypeScript typecheck | P0 |

---

## Phase 4: Frontend Polish & Observability (Week 5–7)

**Goal:** Make the UI production-grade and add operational visibility.

### 4.1 Frontend UX

| # | Ticket | Priority |
|---|--------|----------|
| 51 | Add loading skeleton/spinner on initial data fetch | P0 |
| 52 | Lazy-load Globe component (three.js is ~500KB) with React.lazy + Suspense | P1 |
| 53 | Add error boundaries around Globe, Agent, and Modal components | P0 |
| 54 | Memoize expensive computations (arc filtering, point color mapping) with useMemo/useCallback | P1 |
| 55 | Add responsive layout — mobile/tablet support or graceful "desktop-only" message | P1 |
| 56 | Add URL-based routing (React Router) for shareable/bookmarkable globe state | P2 |
| 57 | Add "no results" empty states for agent queries and empty filtered views | P1 |
| 58 | Move inline styles and magic numbers to shared constants / design tokens | P2 |

### 4.2 Observability

| # | Ticket | Priority |
|---|--------|----------|
| 59 | Add structured logging with request correlation IDs (middleware) | P1 |
| 60 | Add simple admin dashboard page: scrape history, DB row counts, token spend summary | P2 |
| 61 | Add uptime monitoring on `/health` endpoint (UptimeRobot free tier or similar) | P1 |

### 4.3 Security Hardening

| # | Ticket | Priority |
|---|--------|----------|
| 62 | Audit all raw SQL for injection risks — parameterize any string-interpolated queries | P0 |
| 63 | Add API key or lightweight session auth for agent/analysis endpoints | P1 |

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

## Non-Goals (for now)

- Mobile app (web-only is fine)
- User accounts / auth (public dashboard for now, API key auth only)
- Real-time websocket streaming (polling/refresh is sufficient)
- Multi-language support
- Custom event submission by users
