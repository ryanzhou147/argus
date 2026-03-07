## Why

Canada's economic interests are deeply entangled with global events—energy markets, trade routes, commodity prices, geopolitical shifts—yet there is no single tool that visualizes these events geographically, links them relationally, and explains their specific impact on Canada. This MVP builds a hackathon-ready 3D globe dashboard that turns structured event data into an analyst-facing intelligence view. The app assumes event data already exists (seeded/mock for now) and is designed so real ingestion and AWS Postgres can replace the mock layer later without architectural changes.

## What Changes

- Introduce a React 19 + Vite 6 + TypeScript frontend scaffolded from the official create-cloudinary-react starter kit, with Tailwind CSS, react-globe.gl, timeline slider, event filter bar, and event modal/side panel.
- Introduce a FastAPI backend with modular routers, Pydantic response models, service layer, and a repository layer (mock implementation backed by realistic seed data; interface ready for Postgres swap).
- Define and seed a full relational data model (sources, content, entities, events, relationships, engagement) matching the production schema, with 18–24 events, 40–60 content rows, and 30–50 relationships.
- Integrate Cloudinary for event hero images with graceful fallback when credentials are absent.
- Implement read-only API routes: `GET /events`, `GET /events/{id}`, `GET /events/{id}/related`, `GET /filters`, `GET /timeline`.
- Implement globe visualization with event nodes, relationship arcs, timeline-driven playback, event-type filtering, and click-to-open modal.
- No authentication, no write APIs, no scraping, no admin tools.

## Capabilities

### New Capabilities
- `event-data-model`: Relational data model (sources, content, entities, events, relationships, engagement) with seed data layer and repository interface for future Postgres swap.
- `event-api`: FastAPI read-only API serving events, filters, timeline, and related-event data with Pydantic response models.
- `globe-visualization`: 3D globe rendering event nodes and relationship arcs using react-globe.gl, with tooltip hover and click-to-modal interaction.
- `timeline-playback`: Timeline slider controlling which events are visible on the globe based on start_time, supporting drag and auto-play modes.
- `event-filtering`: Filter bar for six event types that updates visible globe nodes and arcs in real time.
- `event-modal`: Side panel / modal displaying full event detail—title, type, location, time, summaries, confidence, hero image (Cloudinary), source cards, related events, entities, and engagement snapshot.
- `cloudinary-media`: Cloudinary integration for event hero images with environment-driven config and local fallback behavior.

### Modified Capabilities
<!-- No existing capabilities to modify — greenfield project. -->

## Impact

- **New directories**: `frontend/` (React app) and `backend/` (FastAPI app) at repo root.
- **Dependencies**: React 19, Vite 6, TypeScript 5, Tailwind CSS, react-globe.gl, Cloudinary React SDK on the frontend; FastAPI, Uvicorn, Pydantic on the backend.
- **APIs**: Five new read-only endpoints under FastAPI with auto-generated OpenAPI docs.
- **Infrastructure**: No live infrastructure required for MVP; code structured for future AWS RDS PostgreSQL + pgvector connection via environment variables.
- **Media**: Cloudinary public IDs / URLs referenced in seed data; credentials loaded from env vars with fallback to placeholder images.
