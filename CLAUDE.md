# Project Rules

## Goal

Build a local-demo MVP for a global event intelligence globe focused on explaining why global events matter to Canada.

## Non-negotiable stack

- Frontend: React 19 + Vite 6 + TypeScript 5
- Frontend must be scaffolded with the official `create-cloudinary-react` starter
- Tailwind CSS
- react-globe.gl
- Backend: FastAPI
- Production database target: AWS PostgreSQL
- Local MVP uses seeded fake data and mock repositories first
- Cloudinary must be visible in the running MVP for event images

## Product constraints

- No auth
- No login
- No admin panel
- No scraping implementation in v1
- No write APIs in v1
- No autonomous agent/copilot in v1

## Required user experience

- 3D globe with clickable event nodes
- Relationship arcs between related events
- Timeline slider with scrub + playback
- Event-type filter bar
- Event modal / side panel
- Modal must show:
  - title
  - event type
  - primary location
  - start/end time
  - summary
  - canada impact summary
  - confidence score
  - hero image
  - top source cards
  - related events
  - key entities
  - engagement snapshot

## Event types

- geopolitics
- trade_supply_chain
- energy_commodities
- financial_markets
- climate_disasters
- policy_regulation

## Relationship types

- market_reaction
- commodity_link
- supply_chain_link
- regional_spillover
- policy_impact
- same_event_family

## Architecture rules

- Frontend must consume FastAPI endpoints, even in local demo mode
- Do not couple frontend directly to local JSON files
- Use a repository/service pattern in backend
- Implement seeded fake data matching the real tables
- Keep structure deployable later to AWS PostgreSQL
- Keep Cloudinary integration non-blocking if credentials are missing

## API routes required

- GET /events
- GET /events/{event_id}
- GET /events/{event_id}/related
- GET /filters
- GET /timeline

## Definition of done

- App runs locally
- Globe renders seeded event nodes
- Arcs render correctly
- Filters work
- Timeline works
- Clicking a node opens a populated modal
- Modal shows Cloudinary-backed media in the running demo
- All UI data is served through FastAPI routes
