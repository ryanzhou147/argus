# Argus — Claude Context File

Read this file before working on any ticket. It contains the full architectural context, conventions, and key file locations for the Argus project.

## What Is Argus

A 3D global event intelligence platform. World events are scraped daily from multiple sources, stored in PostgreSQL with vector embeddings, and visualized on an interactive globe. An AI agent (Graph-RAG pipeline) lets users query events with persona-aware analysis.

## Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Frontend | React 19 + TypeScript 5 + Vite 6 | SPA, no SSR |
| Globe | react-globe.gl (three.js wrapper) | Heavy bundle — lazy-load |
| Styling | Tailwind CSS 3 + CSS custom properties | Design tokens in `index.css` |
| Backend | FastAPI + Uvicorn (Python 3.11+) | Async throughout |
| Database | PostgreSQL 15+ with pgvector + pgcrypto | Extensions required |
| AI Model | Google Gemini 2.5-flash | Structured JSON output |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) | Migration target: local sentence-transformers |
| Voice | ElevenLabs Scribe v1 | Optional, speech-to-text |
| Media | Cloudinary (primary), S3 fallback, placeholder SVGs | |

## Project Structure

```
hackcanada/
├── plan/                              # PRD and this context file
├── frontend/
│   ├── src/
│   │   ├── main.tsx                   # Entry: nested context providers
│   │   ├── App.tsx                    # Bootstrap: fetch points/arcs, render overlays
│   │   ├── index.css                  # Design tokens, fonts
│   │   ├── api/client.ts             # Typed fetch wrapper for all backend endpoints
│   │   ├── components/
│   │   │   ├── Globe/GlobeView.tsx    # 3D globe — points, arcs, tooltips, clusters
│   │   │   ├── Filters/FilterBar.tsx  # Event-type filter chips
│   │   │   ├── Timeline/TimelineSlider.tsx  # Date scrubber + play/pause
│   │   │   ├── Modal/EventModal.tsx   # Right panel — event detail + AI analysis
│   │   │   ├── Modal/RealTimeAnalysisSection.tsx  # Gemini + Google Search grounding
│   │   │   └── Agent/                 # Left panel — AI query interface
│   │   │       ├── AgentPanel.tsx     # Query input, voice, submit
│   │   │       ├── AgentAnswerView.tsx  # Citation parsing, financial impact
│   │   │       ├── AgentNavigationOverlay.tsx  # Globe camera animation
│   │   │       ├── PersonaSelector.tsx  # Role + industry selection
│   │   │       └── FinancialImpactSection.tsx
│   │   ├── context/
│   │   │   ├── AppContext.tsx         # Events, arcs, filters, timeline, globe focus
│   │   │   ├── AgentContext.tsx       # Agent state, highlights, navigation plan
│   │   │   └── UserPersonaContext.tsx # Role + industry (localStorage-persisted)
│   │   ├── types/
│   │   │   ├── events.ts             # Event, ContentPoint, ContentArc, EventDetail
│   │   │   └── agent.ts              # AgentResponse, NavigationPlan, FinancialImpact
│   │   └── utils/mediaConfig.ts      # Cloudinary/S3/placeholder URL resolver
│   └── package.json
│
└── backend/
    ├── requirements.txt
    ├── run_scrape.py                  # CLI: Polymarket + Kalshi scrape
    ├── run_gdelt_scrape.py            # CLI: GDELT scrape (--days, --limit flags)
    ├── migrations/
    │   └── 001_init_schema.sql        # Full PostgreSQL schema
    └── app/
        ├── main.py                    # FastAPI app, CORS, router registration
        ├── config.py                  # Env var loading, agent defaults
        ├── models/
        │   ├── enums.py               # EventType, RelationshipType (StrEnum)
        │   ├── schemas.py             # Core Pydantic models
        │   └── agent_schemas.py       # Agent-specific Pydantic models
        ├── routers/
        │   ├── content.py             # GET /content/points, /arcs, POST /{id}/confidence-score, /{id}/realtime-analysis
        │   ├── agent.py               # POST /agent/query
        │   ├── ingestion.py           # POST /ingestion/acled
        │   ├── embeddings.py          # POST /embeddings/backfill/content
        │   └── market_signals.py      # GET /market-signals (live fetch)
        ├── services/
        │   ├── agent_service.py       # Graph-RAG pipeline orchestration
        │   ├── agent_tools.py         # DB query tools (search, relate, detail, impact)
        │   ├── gemini_client.py       # Gemini API: synthesis, confidence, realtime analysis
        │   ├── scraping_service.py    # Polymarket + Kalshi + GDELT orchestrator
        │   └── content_repository.py  # (duplicate — also in ingestion/)
        ├── repositories/
        │   └── content_repository.py  # Market signal row persistence
        ├── embeddings/
        │   ├── embedding_repository.py       # Fetch/update embedding vectors
        │   ├── embedding_backfill_service.py  # Backfill missing embeddings
        │   ├── openai_embedding_client.py     # OpenAI API wrapper
        │   └── run_embedding_backfill.py      # CLI entry
        ├── ingestion/
        │   ├── ingestion_service.py   # ACLED pipeline: fetch -> normalize -> dedupe -> insert
        │   ├── content_repository.py  # ensure_sources, insert_content (DUPLICATE)
        │   ├── db.py                  # asyncpg connection pool (only used by ingestion)
        │   ├── dedupe_service.py      # Duplicate detection
        │   └── acled/
        │       ├── acled_client.py    # ACLED API client
        │       └── acled_normalizer.py
        └── scrapers/
            ├── gdelt.py               # GDELT (BigQuery primary, DOC API fallback)
            ├── polymarket.py          # Polymarket API
            ├── kalshi.py              # Kalshi API (async, rate-limited)
            ├── row_format.py          # Shared row normalization -> content_table shape
            ├── eonet.py               # UNUSED — delete
            ├── eonet_db.py            # UNUSED — delete
            ├── social_scraper.py      # UNUSED — delete
            ├── reddit.py              # UNUSED — delete
            ├── reddit_classifier.py   # UNUSED — delete
            ├── reddit_db.py           # UNUSED — delete
            ├── Reddit Scraper/        # UNUSED — delete
            ├── natural-disasters/     # UNUSED — delete
            └── ryan_scrapers/         # UNUSED — delete
```

## Database Schema

PostgreSQL with pgvector and pgcrypto extensions.

### Core Tables

**`content_table`** (primary data store — rename target: `articles`)
- `id` UUID PK (gen_random_uuid)
- `title`, `body`, `url` (UNIQUE)
- `latitude`, `longitude` (nullable floats)
- `image_url` (Cloudinary public_id), `s3_url`
- `embedding` vector(1536) — OpenAI text-embedding-3-small
- `sentiment_score` float, `market_signal` text
- `published_at` timestamptz, `event_type` text, `raw_metadata_json` JSONB
- `source_id` FK -> sources, `engagement_id` FK -> engagement
- `created_at` timestamptz

**`engagement`** — Reddit, Polymarket, Twitter metrics per content item

**`sources`** — name, type, base_url, trust_score

**`entities`** — extracted entities (person, org, location, etc.)

**`content_entities`** — join table (content_item_id, entity_id, relevance_score)

**`events`** — clustered event groups with cluster_embedding, canada_impact_summary, confidence_score

**`event_content`** — join between events and content_table

**`event_relationships`** — event_a_id, event_b_id, relationship_type, score, reason_codes

### Key Indexes
- HNSW cosine index on `content_table.embedding`
- UNIQUE on `content_table.url`

## API Endpoints

| Method | Path | Purpose | AI Cost |
|--------|------|---------|---------|
| GET | `/content/points` | All content with lat/lng (last 31 days) | None |
| GET | `/content/arcs?threshold=0.7` | Similarity arcs via pgvector cosine | None |
| GET | `/content/{id}` | Single content item detail | None |
| POST | `/content/{id}/confidence-score` | Gemini credibility scoring (0.31-1.0) | 1 Gemini call |
| POST | `/content/{id}/realtime-analysis` | Gemini + Google Search grounding | 1 Gemini call |
| POST | `/agent/query` | Graph-RAG agent pipeline | 1 Gemini call + 1 OpenAI embed |
| GET | `/market-signals` | Live Polymarket + Kalshi fetch | None |
| POST | `/ingestion/acled` | Trigger ACLED ingestion pipeline | None |
| POST | `/embeddings/backfill/content` | Backfill missing embeddings | N OpenAI calls |
| GET | `/health` | Health check | None |

## Agent Pipeline (Graph-RAG)

1. **Classify query** — pattern match keywords -> query_type (event_explanation, impact_analysis, connection_discovery, entity_relevance)
2. **Seed retrieval** — keyword ILIKE search + pgvector cosine similarity
3. **Graph expansion** — 2-hop: for each seed, find 6 nearest neighbors via pgvector
4. **Context assembly** — full article bodies + financial impact heuristics
5. **Gemini synthesis** — structured JSON output with citations `[cite:UUID]`, navigation plan, financial impact
6. **Post-processing** — filter to globe-navigable events, strip invalid citations

Output schema includes: answer, confidence, caution, query_type, navigation_plan, relevant_event_ids, highlight_relationships, financial_impact, reasoning_steps, cited_event_map.

## Event Types (StrEnum)

```
geopolitics, trade_supply_chain, energy_commodities,
financial_markets, climate_disasters, policy_regulation
```

Each maps to a color in the frontend `EVENT_TYPE_COLORS` constant.

## Data Sources

| Source | What It Provides | Scraper File |
|--------|-----------------|--------------|
| GDELT | Global events from news (BigQuery or DOC API) | `scrapers/gdelt.py` |
| ACLED | Armed conflict events | `ingestion/acled/acled_client.py` |
| Polymarket | Prediction market events + probabilities | `scrapers/polymarket.py` |
| Kalshi | Prediction market events + volumes | `scrapers/kalshi.py` |

## Known Issues & Tech Debt

1. **Duplicate `content_repository.py`** — exists in both `repositories/` and `ingestion/`. Must consolidate.
2. **No shared DB pool** — `ingestion/db.py` has its own pool; other services use inline `asyncpg.connect()`. Need a single shared pool.
3. **Dead scraper code** — `eonet.py`, `reddit*.py`, `social_scraper.py`, `Reddit Scraper/`, `natural-disasters/`, `ryan_scrapers/` are all unused.
4. **No scheduled scraping** — all ingestion is manual CLI or API trigger.
5. **Expensive embeddings** — OpenAI API called per-row. Should switch to local model.
6. **No caching** — every confidence score and realtime analysis call hits Gemini. Need Redis.
7. **CORS wildcard** — `*` origin allowed in production. Must lock down.
8. **No tests** — zero test files in the repo.
9. **Print debugging** — `print()` used instead of structured logging.
10. **No migration tool** — raw SQL files, no Alembic.

## Conventions

### Backend
- **Async everywhere** — use `async def` for all route handlers and service methods
- **asyncpg** for DB access (not SQLAlchemy ORM)
- **Pydantic v2** for request/response models
- **Raw SQL** for queries (no ORM) — parameterize all user inputs with `$1, $2` syntax
- **Environment variables** via `python-dotenv` and `os.getenv()`
- **Scraper output** normalized via `row_format.make_content_row()` before DB insert

### Frontend
- **React 19** with function components and hooks only
- **Context API** for state (no Redux) — three providers: App, Agent, UserPersona
- **Tailwind CSS** for styling — design tokens as CSS variables in `index.css`
- **No routing library** yet — single-page, overlay-based navigation
- **Client-side filtering** — all events loaded on mount, visibility controlled by pointRadius/pointColor

### Git
- Branch from `main`
- Conventional-ish commit messages (e.g., `feat:`, `fix:`, `chore:`)

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname    # Required
GEMINI_API_KEY=...          # Required for agent
GEMINI_MODEL=gemini-2.5-flash  # Optional, default shown
OPENAI_API_KEY=...          # Required for embeddings (until local model migration)
ACLED_API_KEY=...           # Required for ACLED ingestion
CLOUDINARY_CLOUD_NAME=...  # Optional
CLOUDINARY_API_KEY=...     # Optional
CLOUDINARY_API_SECRET=...  # Optional
AWS_ACCESS_KEY_ID=...      # Optional (S3 fallback)
AWS_SECRET_ACCESS_KEY=...  # Optional
S3_BUCKET=...              # Optional
AWS_REGION=...             # Optional
ELEVENLABS_API_KEY=...     # Optional
```

### Frontend (.env)
```
VITE_API_URL=/api                    # or http://127.0.0.1:8000
VITE_CLOUDINARY_CLOUD_NAME=...      # Optional
VITE_ELEVENLABS_API_KEY=...         # Optional
```

## Running Locally

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Manual scraping
python run_scrape.py              # Polymarket + Kalshi
python run_gdelt_scrape.py        # GDELT (--days 14 --limit 500)
curl -X POST localhost:8000/ingestion/acled
curl -X POST localhost:8000/embeddings/backfill/content
```

## Working on Tickets

When picking up a ticket from the PRD (`plan/PRD.md`):

1. **Read the relevant source files first** — don't modify code you haven't read
2. **Check for duplicates** — the codebase has redundant implementations (see Known Issues)
3. **Keep async** — all new backend code should be async
4. **Parameterize SQL** — never string-interpolate user input into queries
5. **No new print()** — use `logging.getLogger(__name__)`
6. **Test what you build** — add tests alongside new code (once pytest is set up)
7. **Budget-conscious** — if a feature involves AI API calls, always consider caching and batching first
