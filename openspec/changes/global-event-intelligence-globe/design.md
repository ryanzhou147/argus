## Context

This is a greenfield hackathon MVP. There is no existing codebase. The product is a read-only 3D globe dashboard that visualizes global events, links related events with arcs, supports time-based playback, and explains each event's relevance to Canada from a business/economic perspective.

The frontend must be scaffolded from the official create-cloudinary-react starter kit, then extended with react-globe.gl, Tailwind CSS, and custom components. The backend is a FastAPI service exposing read-only API routes over mock/seeded data that mirrors the production Postgres schema.

Stakeholders: hackathon team (4 members), judges evaluating demo polish and technical architecture.

Constraints:
- Must run locally without AWS credentials or a live database.
- Cloudinary integration must be visible in the running demo but must not block functionality when credentials are missing.
- Repository layer must be swappable so Postgres can replace seeded data later.
- No authentication, no write APIs, no scraping.

## Goals / Non-Goals

**Goals:**
- Deliver a visually polished, demo-ready 3D globe experience with realistic seeded data.
- Implement a clean FastAPI backend with modular routers, Pydantic models, and a repository abstraction.
- Integrate Cloudinary for event hero images with graceful degradation.
- Structure the codebase so a Postgres + pgvector backend can replace the mock layer without frontend changes.
- Support event filtering by type, timeline-driven playback, relationship arcs, and a detailed event modal.

**Non-Goals:**
- Real-time data ingestion or scraping.
- User authentication or authorization.
- Write/mutation APIs.
- Production deployment or CI/CD pipeline.
- Full-text search or vector similarity queries (pgvector is a future concern).
- Admin tooling or autonomous agent features.

## Decisions

### 1. Monorepo with `frontend/` and `backend/` directories

**Choice:** Single repo, two top-level directories.
**Rationale:** Simplest structure for a hackathon team. No need for separate repos, monorepo tooling, or shared package management. Each directory has its own dependency management (`package.json` / `requirements.txt`).
**Alternatives considered:** Separate repos (overhead), single full-stack framework (doesn't match the required stack).

### 2. Repository pattern with abstract base class in Python

**Choice:** Define an `EventRepository` abstract base class (Python ABC) with methods like `get_events()`, `get_event_by_id()`, `get_related_events()`, etc. Provide a `MockEventRepository` that returns seeded data from Python dictionaries. A future `PostgresEventRepository` will implement the same interface.
**Rationale:** The user requirement explicitly calls for swappable data sources. ABC gives type safety and makes the contract explicit. The mock implementation loads seed data at import time from a `seed_data.py` module.
**Alternatives considered:** SQLAlchemy models with SQLite for local dev (heavier than needed for pure mock data), JSON file-based repository (less flexible, harder to query).

### 3. Seed data as Python dictionaries in `seed_data.py`

**Choice:** All seed data lives in a single `backend/app/data/seed_data.py` file as typed dictionaries conforming to Pydantic models. Data is loaded into the mock repository at startup.
**Rationale:** Keeps seed data co-located with the backend, easily editable, and directly validated against Pydantic models. No file I/O or JSON parsing needed.
**Alternatives considered:** JSON files (lose type hints), database fixtures (requires a running DB), YAML (extra dependency).

### 4. Frontend API client with typed functions

**Choice:** A `frontend/src/api/client.ts` module exporting typed async functions (`getEvents()`, `getEventById()`, etc.) that call the FastAPI backend via `fetch`. Base URL configured via environment variable (`VITE_API_URL`), defaulting to `http://localhost:8000`.
**Rationale:** Keeps API coupling in one place. Typed return values match Pydantic response models. No heavy HTTP library needed.
**Alternatives considered:** Axios (unnecessary weight), React Query (good but adds complexity for a read-only demo), generated OpenAPI client (overkill for 5 endpoints).

### 5. react-globe.gl as the sole globe renderer

**Choice:** Use `react-globe.gl` directly for all globe rendering—point nodes for events, arcs for relationships, HTML tooltips for hover.
**Rationale:** react-globe.gl wraps globe.gl which wraps ThreeJS. It provides declarative React bindings for points, arcs, labels, and custom HTML elements. It supports the exact feature set needed: point click handlers, arc rendering from lat/lng pairs, and programmatic camera control.
**Alternatives considered:** Raw ThreeJS (too low-level), Cesium (heavyweight, overkill), deck.gl (good but react-globe.gl is more purpose-built for this use case).

### 6. Timeline state drives globe filtering

**Choice:** A single `timelinePosition` state (Date) in a shared context/store drives which events are visible. Events with `start_time <= timelinePosition` are shown. The timeline component updates this state via drag or auto-play (setInterval). The globe component and filter bar both read from this state.
**Rationale:** Single source of truth avoids synchronization bugs. React re-renders handle the update cascade naturally.
**Alternatives considered:** Redux (overkill for this scope), URL-based state (unnecessary for a single-page demo).

### 7. Cloudinary via public IDs with environment-driven config

**Choice:** Seed data references Cloudinary public IDs (e.g., `hackcanada/events/red-sea-shipping`). A `mediaConfig.ts` utility builds Cloudinary URLs using the `@cloudinary/url-gen` SDK when `VITE_CLOUDINARY_CLOUD_NAME` is set. When unset, it returns a local placeholder image path.
**Rationale:** Matches the requirement for Cloudinary to be visible in the running demo while not blocking functionality without credentials. Public IDs are stable references that work with Cloudinary's transformation pipeline.
**Alternatives considered:** Hardcoded Cloudinary URLs (brittle, no transformation support), upload widget (out of scope).

### 8. FastAPI modular router structure

**Choice:** `backend/app/main.py` mounts routers from `backend/app/routers/events.py`, `backend/app/routers/filters.py`, `backend/app/routers/timeline.py`. Each router imports from a service layer which imports from the repository.
**Rationale:** Follows FastAPI's documented pattern for larger applications. Keeps endpoint logic thin, business logic in services, data access in repositories.
**Alternatives considered:** Single-file FastAPI app (doesn't scale, harder to navigate).

### 9. Event type and relationship type as string enums

**Choice:** Define `EventType` and `RelationshipType` as Python `StrEnum` and TypeScript string union types. Six event types: `geopolitics`, `trade_supply_chain`, `energy_commodities`, `financial_markets`, `climate_disasters`, `policy_regulation`. Six relationship types: `market_reaction`, `commodity_link`, `supply_chain_link`, `regional_spillover`, `policy_impact`, `same_event_family`.
**Rationale:** Enums enforce valid values at both API boundary and frontend rendering. StrEnum serializes cleanly to JSON.
**Alternatives considered:** Free-form strings (error-prone), numeric codes (less readable).

### 10. CORS middleware for local development

**Choice:** FastAPI app includes `CORSMiddleware` allowing `http://localhost:5173` (Vite dev server default) in development.
**Rationale:** Required for the frontend to call the backend during local development. Standard FastAPI pattern.

## Risks / Trade-offs

- **Seed data staleness** → Mitigated by structuring seed data to be easily regenerated and clearly separated from application logic.
- **react-globe.gl performance with many nodes** → Mitigated by keeping seed data at 18–24 events. Production would need LOD or clustering.
- **Cloudinary free tier limits** → Mitigated by using a small number of seeded images and fallback behavior when credentials are absent.
- **No real database in MVP** → Mitigated by repository abstraction. Switching to Postgres requires implementing one class, no frontend changes.
- **Timeline auto-play smoothness** → Mitigated by using requestAnimationFrame or throttled setInterval with reasonable step sizes.
- **Monorepo without shared types** → Frontend and backend types may drift. Mitigated by keeping Pydantic models and TypeScript interfaces aligned manually; could add OpenAPI codegen later.
