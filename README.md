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

### Backend

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | No* | Google Gemini API key for AI agent features. Get one at https://aistudio.google.com/ — agent returns a graceful fallback response if missing. |

*The app runs without it. Agent features degrade gracefully to internal-data-only answers.

### Frontend

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
│       ├── config.py         # GEMINI_API_KEY + agent config
│       ├── models/           # Pydantic schemas, enums, agent_schemas
│       ├── routers/          # GET /events, /filters, /timeline + POST /agent/query
│       ├── services/         # event_service, agent_service, gemini_client, agent_tools
│       ├── repositories/     # Abstract base + MockEventRepository (with update + text search)
│       └── data/             # seed_data.py (20 events, 50 articles, 40 relationships)
└── frontend/                 # React 19 + Vite 6 + TypeScript 5
    └── src/
        ├── api/client.ts     # Typed fetch calls to FastAPI (incl. postAgentQuery)
        ├── types/            # events.ts + agent.ts TypeScript interfaces
        ├── context/          # AppContext (timeline, filters, auto-spin) + AgentContext
        ├── utils/mediaConfig.ts  # Cloudinary URL builder with fallback
        └── components/
            ├── Globe/        # react-globe.gl with event nodes, arcs, agent pulse/highlight
            ├── Timeline/     # Scrub + play/pause timeline slider
            ├── Filters/      # Event-type filter bar
            ├── Modal/        # Event detail side panel + financial impact section
            └── Agent/        # AgentLauncherButton, AgentPanel, AgentAnswerView,
                              # AgentNavigationOverlay, FinancialImpactSection
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/events` | List events (filter by type, start_time, end_time) |
| GET | `/events/{id}` | Full event detail (sources, entities, engagement, related) |
| GET | `/events/{id}/related` | Related events with relationship metadata |
| GET | `/filters` | Available event types and relationship types |
| GET | `/timeline` | All events ordered by start_time with min/max bounds |
| POST | `/agent/query` | AI agent: classify, retrieve, Gemini synthesis, globe navigation plan |

## AI Agent

The AI Globe Copilot is accessible via the brain icon in the top-right corner.

**What it does:**
- Answers natural-language questions about global events and their impact on Canada
- Navigates the globe cinematically to relevant events (camera, pulse nodes, highlight arcs, auto-open modal)
- Returns structured confidence signals (high/medium/low) and caution banners for low-confidence answers
- Falls back to cited external sources when internal data is insufficient
- Supports controlled mock-data updates for the local demo

**Query types:**
- `event_explanation` — "Why did the OPEC production cut happen?"
- `impact_analysis` — "What is the financial impact of the Red Sea disruption on Canada?"
- `connection_discovery` — "What events are related to semiconductor export controls?"
- `entity_relevance` — "What does this mean for Canadian oil?"
- `update_request` — "Update the impact note for the OPEC event to..."

**Setup with Gemini:**
```bash
export GEMINI_API_KEY=your_key_here
uvicorn app.main:app --reload --port 8000
```

Without the key, the agent returns a graceful low-confidence response and the rest of the app continues to function normally.

## Event Types

- `geopolitics` — Red (military, diplomatic)
- `trade_supply_chain` — Orange (ports, shipping, logistics)
- `energy_commodities` — Yellow (oil, gas, potash)
- `financial_markets` — Green (central banks, currencies)
- `climate_disasters` — Blue (wildfires, floods, hurricanes)
- `policy_regulation` — Purple (legislation, trade rules, sanctions)

## Swapping to Postgres

Implement `PostgresEventRepository` in `backend/app/repositories/postgres.py` extending `EventRepository`, then update `backend/app/dependencies.py` to return your new class. No frontend or router changes needed.
