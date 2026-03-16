# Argus Deployment Issue Board

This board is derived from the deployment planning work merged from PR #29 (`plan/PRD.md` and `plan/CLAUDE.md`).

## Current Status

- Total unique deployment-plan tasks tracked: **66**
- Completed: **0**
- Remaining: **66**

## Deployment Blockers (P0)

> These are a prioritized subset of the full board and are duplicated below in the phase checklists.

- [ ] #1 Create backend Dockerfile (FastAPI + uvicorn, multi-stage build)
- [ ] #2 Create frontend Dockerfile (Vite build -> nginx static serve)
- [ ] #3 Create `docker-compose.yml` with backend, frontend, postgres+pgvector, redis
- [ ] #4 Add `.dockerignore` files
- [ ] #5 Set up GitHub Actions CI (ruff lint/format, TypeScript typecheck, docker build)
- [ ] #8 Delete junk scrapers (`eonet.py`, `eonet_db.py`, `social_scraper.py`, `reddit.py`, `reddit_classifier.py`, `reddit_db.py`, `reddit_schema.sql`, `Reddit Scraper/`, `natural-disasters/`, `ryan_scrapers/`)
- [ ] #9 Move remaining hackathon scrapers into `scrapers/_reference/`
- [ ] #10 Remove duplicate `content_repository.py` and consolidate
- [ ] #11 Remove Cloudinary and S3 media code, deps, env vars, DB columns
- [ ] #13 Lock down CORS origins (remove wildcard `*`, use env-configured origins)
- [ ] #14 Add rate limiting for expensive AI endpoints
- [ ] #15 Enforce required secrets via env vars and fail fast on startup
- [ ] #16 Design `BaseScraper` ABC with rate limiting/error handling/dedup
- [ ] #17 Implement new production scrapers using `BaseScraper`
- [ ] #18 Create unified pipeline entrypoint (`run_daily_pipeline.py`)
- [ ] #19 Add scrape scheduler (APScheduler/cron)
- [ ] #20 Define scrape schedule per source
- [ ] #22 Add idempotency guards (URL dedup before insert)
- [ ] #24 Switch embeddings to local `sentence-transformers` model
- [ ] #25 Batch embedding generation
- [ ] #27 Add Redis client utility with pooling
- [ ] #28 Cache `/content/points`
- [ ] #30 Cache Gemini confidence scores
- [ ] #31 Cache realtime analysis
- [ ] #36 Set up Alembic migrations
- [ ] #43 Create shared DB pool module for all services
- [ ] #47 Set up pytest with async fixtures
- [ ] #48 Add scraper/normalization tests
- [ ] #53 Add pre-commit hooks (ruff + TS typecheck)
- [ ] #54 Add initial loading UI state
- [ ] #56 Add frontend error boundaries
- [ ] #65 Audit and parameterize raw SQL for injection safety

## Full Board (All PR #29 Planning Tasks)

### Phase 1 — Foundation (Week 1–2)

- [ ] #1 Create backend Dockerfile (P0)
- [ ] #2 Create frontend Dockerfile (P0)
- [ ] #3 Create `docker-compose.yml` with backend, frontend, postgres+pgvector, redis (P0)
- [ ] #4 Add `.dockerignore` files (P0)
- [ ] #5 Set up GitHub Actions CI (P0)
- [ ] #6 Set up GitHub Actions CD (P1)
- [ ] #7 Choose hosting provider + document deploy process (P1)
- [ ] #8 Delete junk scrapers (P0)
- [ ] #9 Move reference scrapers to `scrapers/_reference/` (P0)
- [ ] #10 Consolidate duplicate `content_repository.py` (P0)
- [ ] #11 Remove Cloudinary/S3 media code and related schema/env/deps (P0)
- [ ] #12 Audit/remove remaining dead code (P1)
- [ ] #13 Lock down CORS origins (P0)
- [ ] #14 Add endpoint rate limiting (P0)
- [ ] #15 Validate required env secrets on startup (P0)

### Phase 2 — Automation & Cost Optimization (Week 2–3)

- [ ] #16 Design `BaseScraper` ABC (P0)
- [ ] #17 Write production scrapers implementing `BaseScraper` (P0)
- [ ] #18 Build `run_daily_pipeline.py` (P0)
- [ ] #19 Add scheduler (P0)
- [ ] #20 Define scraping schedule (P0)
- [ ] #21 Add `scrape_runs` logging table (P1)
- [ ] #22 Add pre-insert URL dedup/idempotency guard (P0)
- [ ] #23 Add scrape failure alerting (P2)
- [ ] #24 Replace OpenAI embeddings with local sentence-transformers (P0)
- [ ] #25 Batch embedding generation (P0)
- [ ] #26 Deduplicate before embedding generation (P1)
- [ ] #27 Add Redis client utility (P0)
- [ ] #28 Cache `/content/points` (P0)
- [ ] #29 Cache `/content/arcs` by threshold (P1)
- [ ] #30 Cache Gemini confidence scores (P0)
- [ ] #31 Cache realtime analysis by `(content_id, user_role)` (P0)
- [ ] #32 Cache agent query results by normalized query + persona (P1)
- [ ] #33 Track token usage in DB (P1)
- [ ] #34 Precompute confidence scores in pipeline (P2)
- [ ] #35 Replace per-request grounding with cached daily summaries (P2)

### Phase 3 — Schema & Code Quality (Week 3–5)

- [ ] #36 Set up Alembic migration management (P0)
- [ ] #37 Rename `content_table` -> `articles` (P1)
- [ ] #38 Move AI fields to `article_analysis` table (P1)
- [ ] #39 Add `scrape_source` enum column (P2)
- [ ] #40 Add index on `(event_type, published_at)` (P1)
- [ ] #41 Add `last_scraped_at` on sources (P2)
- [ ] #42 Remove remaining unused schema artifacts (P1)
- [ ] #43 Create shared `db.py` pool module (P0)
- [ ] #44 Consolidate Pydantic models under `schemas/` (P1)
- [ ] #45 Replace `print()` with structured logging + correlation IDs (P1)
- [ ] #46 Add stronger endpoint input validation (P1)
- [ ] #47 Set up pytest with async fixtures (P0)
- [ ] #48 Add tests for new scrapers + normalization (P0)
- [ ] #49 Add deduplication tests (P1)
- [ ] #50 Add `_classify_query` tests (P1)
- [ ] #51 Add API integration tests (`/content/points`, `/agent/query`) (P1)
- [ ] #52 Add frontend smoke tests with Vitest + RTL (P2)
- [ ] #53 Add pre-commit hooks (P0)

### Phase 4 — Frontend Polish & Observability (Week 5–7)

- [ ] #54 Add loading skeleton/spinner on initial fetch (P0)
- [ ] #55 Lazy-load Globe with `React.lazy` + `Suspense` (P1)
- [ ] #56 Add error boundaries around Globe, Agent, Modal (P0)
- [ ] #57 Memoize expensive computations (P1)
- [ ] #58 Add responsive/mobile support or desktop-only message (P1)
- [ ] #59 Add URL-based routing for shareable state (P2)
- [ ] #60 Add empty states for agent/filter no-results (P1)
- [ ] #61 Move inline styles/magic numbers to constants/tokens (P2)
- [ ] #62 Add structured logging middleware with correlation IDs (P1)
- [ ] #63 Add admin dashboard (scrape history/row counts/token spend) (P2)
- [ ] #64 Add uptime monitoring on `/health` (P1)
- [ ] #65 Audit SQL injection risks and parameterize all queries (P0)
- [ ] #66 Add API key/lightweight auth for agent/analysis endpoints (P1)
