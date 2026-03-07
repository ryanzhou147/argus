## 1. Project Scaffolding

- [ ] 1.1 Scaffold frontend using create-cloudinary-react starter kit into `frontend/` directory
- [ ] 1.2 Add React 19, Vite 6, TypeScript 5, Tailwind CSS configuration to the frontend
- [ ] 1.3 Install frontend dependencies: react-globe.gl, @cloudinary/url-gen, @cloudinary/react
- [ ] 1.4 Create `backend/` directory with FastAPI project structure: `app/main.py`, `app/routers/`, `app/services/`, `app/repositories/`, `app/models/`, `app/data/`
- [ ] 1.5 Create `backend/requirements.txt` with FastAPI, uvicorn, pydantic
- [ ] 1.6 Configure CORS middleware in FastAPI allowing `http://localhost:5173`

## 2. Backend Data Models & Enums

- [ ] 2.1 Define `EventType` StrEnum with six event types in `app/models/enums.py`
- [ ] 2.2 Define `RelationshipType` StrEnum with six relationship types in `app/models/enums.py`
- [ ] 2.3 Create Pydantic models for Source, ContentItem, Entity, ContentEntity in `app/models/schemas.py`
- [ ] 2.4 Create Pydantic models for Event, EventDetail, EventRelationship, Engagement in `app/models/schemas.py`
- [ ] 2.5 Create Pydantic response models for list endpoints (EventListResponse, FilterResponse, TimelineResponse, RelatedEventsResponse) in `app/models/schemas.py`

## 3. Seed Data

- [ ] 3.1 Create `app/data/seed_data.py` with 8–10 source records
- [ ] 3.2 Add 40–60 content rows representing articles from seeded sources with valid coordinates, event types, and timestamps
- [ ] 3.3 Add 20–30 canonical entity records (countries, organizations, commodities, people)
- [ ] 3.4 Add content-entity association records with relevance scores
- [ ] 3.5 Add 18–24 clustered event records covering all six event types with coordinates, time bounds, summaries, Canada impact summaries, confidence scores, and Cloudinary image public IDs
- [ ] 3.6 Add event-content link records (at least 2 content items per event)
- [ ] 3.7 Add 30–50 event relationship records using all six relationship types with scores and reason codes
- [ ] 3.8 Add engagement records for each event with reddit and poly metrics

## 4. Repository Layer

- [ ] 4.1 Define abstract `EventRepository` base class in `app/repositories/base.py` with methods: `get_events()`, `get_event_by_id()`, `get_related_events()`, `get_filters()`, `get_timeline()`, `get_event_detail()`
- [ ] 4.2 Implement `MockEventRepository` in `app/repositories/mock.py` loading seed data and implementing all abstract methods with filtering and lookup logic
- [ ] 4.3 Create repository dependency injection in `app/dependencies.py` returning MockEventRepository instance

## 5. Backend Service Layer

- [ ] 5.1 Create `app/services/event_service.py` with service functions that call the repository and apply filtering by event_type, start_time, end_time
- [ ] 5.2 Create service function to assemble full event detail payload (event + sources + entities + relationships + engagement)

## 6. Backend API Routes

- [ ] 6.1 Implement `GET /events` router in `app/routers/events.py` with event_type, start_time, end_time query params
- [ ] 6.2 Implement `GET /events/{event_id}` returning full modal payload
- [ ] 6.3 Implement `GET /events/{event_id}/related` returning related events with relationship metadata
- [ ] 6.4 Implement `GET /filters` router in `app/routers/filters.py` returning event types and relationship types
- [ ] 6.5 Implement `GET /timeline` router in `app/routers/timeline.py` returning events ordered by start_time
- [ ] 6.6 Register all routers in `app/main.py` and verify FastAPI OpenAPI docs at `/docs`

## 7. Frontend TypeScript Types & API Client

- [ ] 7.1 Define TypeScript interfaces matching Pydantic models in `src/types/events.ts` (Event, EventDetail, RelatedEvent, Source, Entity, Engagement, etc.)
- [ ] 7.2 Define EventType and RelationshipType union types in `src/types/events.ts`
- [ ] 7.3 Create typed API client in `src/api/client.ts` with functions: `getEvents()`, `getEventById()`, `getRelatedEvents()`, `getFilters()`, `getTimeline()` calling FastAPI backend via fetch with `VITE_API_URL` base

## 8. Cloudinary Media Config

- [ ] 8.1 Create `src/utils/mediaConfig.ts` that builds Cloudinary URLs from public IDs when `VITE_CLOUDINARY_CLOUD_NAME` is set and returns fallback placeholder URLs when absent
- [ ] 8.2 Add placeholder image(s) to `public/` directory for fallback use
- [ ] 8.3 Create `.env.example` with `VITE_CLOUDINARY_CLOUD_NAME` and `VITE_API_URL` variables documented

## 9. Globe Component

- [ ] 9.1 Create `src/components/Globe/GlobeView.tsx` rendering react-globe.gl with full-screen layout
- [ ] 9.2 Implement point nodes from event data with color-coded event types
- [ ] 9.3 Implement arc rendering from relationship data connecting related event coordinates
- [ ] 9.4 Implement node click handler that triggers event modal open
- [ ] 9.5 Implement hover tooltip showing event title and type
- [ ] 9.6 Connect globe to timeline and filter state so it reactively re-renders on changes

## 10. Timeline Component

- [ ] 10.1 Create `src/components/Timeline/TimelineSlider.tsx` with a range slider spanning the full event time range
- [ ] 10.2 Implement drag mode for manual scrubbing
- [ ] 10.3 Implement play/pause mode with auto-advancing timeline position
- [ ] 10.4 Expose timeline position state via React context or shared store
- [ ] 10.5 Position timeline at the bottom of the viewport overlaying the globe

## 11. Filter Bar Component

- [ ] 11.1 Create `src/components/Filters/FilterBar.tsx` with toggleable buttons for all six event types
- [ ] 11.2 Implement active/inactive visual states for each filter button with event-type colors
- [ ] 11.3 Expose active filters state via React context or shared store
- [ ] 11.4 Position filter bar at the top or side of the viewport overlaying the globe

## 12. Event Modal / Side Panel

- [ ] 12.1 Create `src/components/Modal/EventModal.tsx` as a side panel or modal overlay
- [ ] 12.2 Display event title, event type badge, primary location, and time range
- [ ] 12.3 Display event summary and Canada impact summary sections
- [ ] 12.4 Display confidence score as a visual indicator
- [ ] 12.5 Render hero image via Cloudinary media config with fallback
- [ ] 12.6 Display source cards with source name, headline, publication time, and clickable URL
- [ ] 12.7 Display related events list with title, relationship type, score, and reason
- [ ] 12.8 Display key entity chips from canonical entity names
- [ ] 12.9 Display engagement snapshot (reddit upvotes, comments, poly volume, comments)
- [ ] 12.10 Implement close behavior (close button and Escape key)

## 13. App Shell & Layout

- [ ] 13.1 Create shared state context/provider for timeline position, active filters, and selected event
- [ ] 13.2 Compose App layout: globe (full-screen), filter bar (overlay top), timeline (overlay bottom), modal (overlay side), legend
- [ ] 13.3 Create event type legend component with color mapping
- [ ] 13.4 Implement loading and empty states for data fetching

## 14. Integration & Polish

- [ ] 14.1 Wire up frontend to fetch from FastAPI backend on app load
- [ ] 14.2 Verify end-to-end: events load → globe renders nodes → filters work → timeline scrubs → click opens modal → modal shows all fields → arcs render
- [ ] 14.3 Add README.md with setup instructions for both frontend and backend
- [ ] 14.4 Test fallback behavior when Cloudinary credentials are absent
