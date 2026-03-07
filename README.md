# Global Event Intelligence Globe — Canada Impact

A hackathon MVP: a 3D globe dashboard that visualizes global events and explains why they matter to Canada.

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Optional: add your Cloudinary cloud name to .env
npm run dev
```

App runs at: http://localhost:5173

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | No | FastAPI backend URL. Defaults to `http://localhost:8000` |
| `VITE_CLOUDINARY_CLOUD_NAME` | No | Cloudinary cloud name for event hero images. Falls back to placeholder SVG when absent. |

## Architecture

```
hackcanada/
├── backend/                  # FastAPI backend
│   └── app/
│       ├── main.py           # FastAPI app + CORS
│       ├── models/           # Pydantic schemas + enums
│       ├── routers/          # GET /events, /filters, /timeline
│       ├── services/         # Business logic
│       ├── repositories/     # Abstract base + MockEventRepository
│       └── data/             # seed_data.py (20 events, 50 articles, 40 relationships)
└── frontend/                 # React 19 + Vite 6 + TypeScript 5
    └── src/
        ├── api/client.ts     # Typed fetch calls to FastAPI
        ├── types/events.ts   # TypeScript interfaces matching Pydantic models
        ├── context/          # AppContext (timeline, filters, selected event)
        ├── utils/mediaConfig.ts  # Cloudinary URL builder with fallback
        └── components/
            ├── Globe/        # react-globe.gl with event nodes + arcs
            ├── Timeline/     # Scrub + play/pause timeline slider
            ├── Filters/      # Event-type filter bar
            └── Modal/        # Event detail side panel
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/events` | List events (filter by type, start_time, end_time) |
| GET | `/events/{id}` | Full event detail (sources, entities, engagement, related) |
| GET | `/events/{id}/related` | Related events with relationship metadata |
| GET | `/filters` | Available event types and relationship types |
| GET | `/timeline` | All events ordered by start_time with min/max bounds |

## Event Types

- `geopolitics` — Red (military, diplomatic)
- `trade_supply_chain` — Orange (ports, shipping, logistics)
- `energy_commodities` — Yellow (oil, gas, potash)
- `financial_markets` — Green (central banks, currencies)
- `climate_disasters` — Blue (wildfires, floods, hurricanes)
- `policy_regulation` — Purple (legislation, trade rules, sanctions)

## Swapping to Postgres

Implement `PostgresEventRepository` in `backend/app/repositories/postgres.py` extending `EventRepository`, then update `backend/app/dependencies.py` to return your new class. No frontend or router changes needed.
