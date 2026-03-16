# Argus — Deployment Issue Board

All tasks required before this project can be deployed to production, extracted from the PRD and PR review discussions. Organized by phase and priority.

**Priority key:** P0 = must-have for deployment · P1 = high value · P2 = nice to have

---

## Phase 1 — Foundation (Week 1–2)

### 1.1 Containerization

- [ ] **#1** `[P0]` Create backend Dockerfile (FastAPI + uvicorn, multi-stage build)
- [ ] **#2** `[P0]` Create frontend Dockerfile (Vite build → nginx static serve)
- [ ] **#3** `[P0]` Create `docker-compose.yml` with services: backend, frontend, postgres+pgvector, redis
- [ ] **#4** `[P0]` Add `.dockerignore` files (exclude `.env`, `node_modules`, `.venv`, `__pycache__`)

### 1.2 CI/CD

- [ ] **#5** `[P0]` Set up GitHub Actions CI: ruff lint/format, TypeScript typecheck, docker build
- [ ] **#6** `[P1]` Set up GitHub Actions CD: build images, push to registry, deploy to hosting
- [ ] **#7** `[P1]` Choose hosting provider (Railway, Fly.io, or small VPS) and document deploy process

### 1.3 Dead Code Removal

- [ ] **#8** `[P0]` Delete junk scrapers: `eonet.py`, `eonet_db.py`, `social_scraper.py`, `reddit.py`, `reddit_classifier.py`, `reddit_db.py`, `reddit_schema.sql`, `Reddit Scraper/`, `natural-disasters/`, `ryan_scrapers/`
- [ ] **#9** `[P0]` Move remaining hackathon scrapers (`gdelt.py`, `kalshi.py`, `polymarket.py`, `acled/`) into a `scrapers/_reference/` directory — kept as design inspiration only
- [ ] **#10** `[P0]` Remove duplicate `content_repository.py` (exists in both `repositories/` and `ingestion/`) — consolidate into one
- [ ] **#11** `[P0]` Remove all Cloudinary and legacy S3 media code — delete `utils/mediaConfig.ts`, remove `@cloudinary/react` and `@cloudinary/url-gen` from frontend, remove `cloudinary` and `boto3` from backend, drop `image_url` and `s3_url` columns from `content_table`, remove all `CLOUDINARY_*` and `AWS_*`/`S3_*` env vars. **Note (from review):** team confirmed S3 *will* be used for media storage, so keep `image_url` (repurposed as the S3 URL column) but drop `s3_url` as a duplicate.
- [ ] **#12** `[P1]` Audit and remove any other dead imports, unused functions, or commented-out code

### 1.4 Security Baseline

- [ ] **#13** `[P0]` Lock down CORS origins — remove `*` wildcard, use env-configured allowed origins
- [ ] **#14** `[P0]` Add rate limiting middleware on `/agent/query` and `/content/{id}/realtime-analysis` (these burn AI tokens)
- [ ] **#15** `[P0]` Validate all secrets are loaded from env vars; fail fast on startup if required vars are missing

---

## Phase 2 — Automation & Cost Optimization (Week 2–3)

### 2.1 Scheduled Scraping

- [ ] **#16** `[P0]` Design `BaseScraper` ABC interface: `async fetch() -> list[NormalizedRow]` with built-in rate limiting, error handling, and dedup. Use `kalshi.py` rate limiter and `ingestion_service.py` error patterns as reference.
- [ ] **#17** `[P0]` Write new production scrapers implementing `BaseScraper` for each data source (determine which sources to keep/add based on product needs)
- [ ] **#18** `[P0]` Create unified scrape entrypoint (`run_daily_pipeline.py`) that runs all scrapers + embedding backfill in sequence
- [ ] **#19** `[P0]` Add cron scheduler (APScheduler in a separate container, or cron in docker-compose)
- [ ] **#20** `[P0]` Define scraping schedule (e.g. 1×/day, 2×/day per source)
- [ ] **#21** `[P1]` Add `scrape_runs` logging table (source, status, rows_inserted, errors, duration_ms, started_at)
- [ ] **#22** `[P0]` Add idempotency guards — URL-based dedup check before insert, not after
- [ ] **#23** `[P2]` Add failure alerting (Discord webhook or email on scrape errors)
- [ ] **#24 (extra)** `[P0]` Add a locking mechanism to `run_daily_pipeline.py` so that if one cron run hangs, the next scheduled run does not spawn a zombie process. Options include a PostgreSQL advisory lock (`pg_try_advisory_lock`) for simplicity or a Redis-based distributed lock. See discussion on PR #29.

### 2.2 Embedding Cost Reduction

- [ ] **#25** `[P0]` Switch embeddings to local model — replace OpenAI `text-embedding-3-small` with `sentence-transformers` (e.g. `all-MiniLM-L6-v2`, 384 dims). Run locally in backend container. Update vector column dimension.
- [ ] **#26** `[P0]` Batch embedding generation — process 100+ items per batch instead of one-at-a-time
- [ ] **#27** `[P1]` Deduplicate content before generating embeddings (currently embeddings are generated before dedup)

### 2.3 AI Response Caching (Redis)

- [ ] **#28** `[P0]` Add Redis client utility module with connection pooling
- [ ] **#29** `[P0]` Cache `/content/points` response — invalidate on new scrape run completion
- [ ] **#30** `[P1]` Cache `/content/arcs` response per threshold value (TTL = until next scrape)
- [ ] **#31** `[P0]` Cache Gemini confidence scores per content_id (TTL = 24h)
- [ ] **#32** `[P0]` Cache Gemini realtime analysis per `(content_id, user_role)` (TTL = 6h)
- [ ] **#33** `[P1]` Cache agent query results keyed on `(normalized_query_hash, persona)` (TTL = 1h)

### 2.4 Additional Cost Controls

- [ ] **#34** `[P1]` Add token usage tracking — log Gemini and OpenAI (if still used) token counts per call to a `token_usage` table
- [ ] **#35** `[P2]` Pre-compute confidence scores during scrape pipeline instead of on-demand per user click
- [ ] **#36** `[P2]` Replace per-request Google Search grounding with daily cached news summaries scraped during pipeline

### 2.5 Globe Performance (from PR review)

- [ ] **#37 (extra)** `[P1]` Implement server-side viewport filtering for `/content/points` (e.g. `?bbox=west,south,east,north&zoom=level`) so only visible points are returned, preventing huge JSON payloads that lag low-end machines. Combine nearby points into clusters when zoom is low; show individual points when zoomed in.

---

## Phase 3 — Schema & Code Quality (Week 3–5)

### 3.1 Database Schema Improvements

- [ ] **#38** `[P0]` Set up Alembic for migration management (replace raw SQL files)
- [ ] **#39** `[P1]` Rename `content_table` → `articles`
- [ ] **#40** `[P1]` Split AI-generated fields into `article_analysis` table (embedding, sentiment_score, market_signal, confidence_score)
- [ ] **#41** `[P2]` Add `scrape_source` enum column to replace generic FK to `sources` table
- [ ] **#42** `[P1]` Add composite index on `(event_type, published_at)` for filtered timeline queries
- [ ] **#43** `[P2]` Add `last_scraped_at` column to sources for freshness tracking
- [ ] **#44** `[P1]` Clean up unused columns and tables from hackathon iteration (including dropped `s3_url`)

### 3.2 Backend Modularization

- [ ] **#45** `[P0]` Create shared `db.py` module — single asyncpg pool used by all services (currently duplicated in `ingestion/db.py` and inline connects). **Important (from review):** explicitly set `max_size` on the connection pool (default asyncpg max is 10) to avoid "too many connections" errors under load. Document the chosen value and the reasoning in the module.
- [ ] **#46** `[P1]` Consolidate all Pydantic models into a single `schemas/` package
- [ ] **#47** `[P1]` Replace all `print()` statements with structured `logging` (use correlation IDs per request)
- [ ] **#48** `[P1]` Add input validation on all API endpoints (query length limits, coordinate bounds, UUID format)
- [ ] **#49** `[P0]` Migrate all sync psycopg2 route handlers to async (`content.py` currently uses `def get_content_points()` / `def get_content_arcs()` with `psycopg2.connect()`). All new code must use asyncpg.

### 3.3 Testing

- [ ] **#50** `[P0]` Set up pytest with async fixtures (asyncpg test DB, httpx AsyncClient)
- [ ] **#51** `[P0]` Write tests for new scraper implementations and row normalization
- [ ] **#52** `[P1]` Write tests for deduplication logic
- [ ] **#53** `[P1]` Write tests for agent query classification (`_classify_query`)
- [ ] **#54** `[P1]` Write API integration tests for `/content/points`, `/agent/query`
- [ ] **#55** `[P2]` Add frontend smoke tests (Vitest + React Testing Library) for Globe render, Agent query flow
- [ ] **#56** `[P0]` Add pre-commit hooks: ruff lint+format, TypeScript typecheck

---

## Phase 4 — Frontend Polish & Observability (Week 5–7)

### 4.1 Frontend UX

- [ ] **#57** `[P0]` Add loading skeleton/spinner on initial data fetch
- [ ] **#58** `[P1]` Lazy-load Globe component (three.js is ~500 KB) with `React.lazy` + `Suspense`
- [ ] **#59** `[P0]` Add error boundaries around Globe, Agent, and Modal components
- [ ] **#60** `[P1]` Memoize expensive computations (arc filtering, point color mapping) with `useMemo`/`useCallback`
- [ ] **#61** `[P1]` Add responsive layout — mobile/tablet support or graceful "desktop-only" message
- [ ] **#62** `[P2]` Add URL-based routing (React Router) for shareable/bookmarkable globe state
- [ ] **#63** `[P1]` Add "no results" empty states for agent queries and empty filtered views
- [ ] **#64** `[P2]` Move inline styles and magic numbers to shared constants / design tokens

### 4.2 Observability

- [ ] **#65** `[P1]` Add structured logging with request correlation IDs (middleware)
- [ ] **#66** `[P2]` Add simple admin dashboard page: scrape history, DB row counts, token spend summary
- [ ] **#67** `[P1]` Add uptime monitoring on `/health` endpoint (UptimeRobot free tier or similar)

### 4.3 Security Hardening

- [ ] **#68** `[P0]` Audit all raw SQL for injection risks — parameterize any string-interpolated queries
- [ ] **#69** `[P1]` Add API key or lightweight session auth for agent/analysis endpoints

---

## Environment & Configuration

- [ ] **#70** `[P0]` Set `DATABASE_URL` to `postgresql://user:pass@host:5432/dbname` (no `+asyncpg` suffix) — both psycopg2 and asyncpg consume it as a standard libpq DSN. Update all documentation and `.env.example` to reflect this.
- [ ] **#71** `[P0]` Add all required environment variables to `.env.example` with comments: `DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OPENAI_API_KEY` (until local embeddings), `ACLED_API_KEY`, `ELEVENLABS_API_KEY` (optional). Remove any `CLOUDINARY_*`, `AWS_*`, `S3_*` examples.

---

## P0 Summary — Must Complete Before First Deploy

The following P0 items are the minimum required to go live:

| # | Task |
|---|------|
| 1 | Backend Dockerfile |
| 2 | Frontend Dockerfile |
| 3 | docker-compose.yml |
| 4 | .dockerignore files |
| 5 | GitHub Actions CI |
| 8 | Delete junk scrapers |
| 10 | Consolidate duplicate content_repository.py |
| 13 | Lock down CORS origins |
| 14 | Rate limiting on AI endpoints |
| 15 | Fail-fast on missing env vars |
| 16 | BaseScraper ABC interface |
| 17 | New production scrapers |
| 18 | run_daily_pipeline.py entrypoint |
| 19 | Cron scheduler |
| 20 | Define scraping schedule |
| 22 | URL-based dedup before insert |
| 24 | Pipeline locking mechanism |
| 25 | Switch to local embeddings (sentence-transformers) |
| 26 | Batch embedding generation |
| 28 | Redis client utility module |
| 29 | Cache /content/points |
| 31 | Cache Gemini confidence scores |
| 32 | Cache Gemini realtime analysis |
| 38 | Set up Alembic migrations |
| 45 | Shared asyncpg DB pool with explicit max_size |
| 49 | Migrate sync psycopg2 routes to async |
| 50 | pytest async fixtures |
| 51 | Scraper + normalization tests |
| 56 | Pre-commit hooks (ruff + TS typecheck) |
| 57 | Loading skeleton on initial fetch |
| 59 | Error boundaries (Globe, Agent, Modal) |
| 68 | Audit raw SQL for injection risks |
| 70 | Fix DATABASE_URL format in docs |
| 71 | Update .env.example |
