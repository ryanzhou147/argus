# Argus

**Argus** is a 3D global event intelligence dashboard that visualizes world events and explains why they matter to Canada. Named after the all-seeing giant of Greek mythology, Argus monitors the world and surfaces geopolitical, economic, climate, and policy events, before connecting them to Canadian impact through an AI analysis layer.

---

## Architecture

**Frontend**
```mermaid
flowchart LR
    App["App.tsx"] --> AppCtx["AppContext"]
    App --> AgentCtx["AgentContext"]
    App --> PersonaCtx["UserPersonaContext"]
    App --> APIClient["api/client.ts"]

    AppCtx --> Globe["GlobeView"]
    AppCtx --> FilterBar["FilterBar"]
    AppCtx --> Timeline["TimelineSlider"]
    AgentCtx --> AgentPanel["AgentPanel"]
    AgentCtx --> NavOverlay["AgentNavigationOverlay"]
    APIClient --> Modal["EventModal"]

    Globe --> MediaCfg["mediaConfig.ts"]
    Modal --> MediaCfg
```

**Backend**
```mermaid
flowchart LR
    Main["main.py"] --> Content["/content"]
    Main --> AgentRouter["/agent"]
    Main --> Market["/market-signals"]
    Main --> Ingest["/ingestion"]
    Main --> Embed["/embeddings"]

    Content --> GeminiClient["gemini_client.py"]
    Content --> AgentTools["agent_tools.py"]
    AgentRouter --> AgentSvc["agent_service.py"]
    AgentSvc --> GeminiClient
    AgentSvc --> AgentTools
    Market --> ScrapeSvc["scraping_service.py"]
    Ingest --> IngestSvc["ingestion_service.py"]
    Embed --> EmbedRepo["embedding_repository.py"]
```

**Data Ingestion**
```mermaid
flowchart LR
    ACLEDApi["ACLED API"] --> IngestSvc["ingestion_service.py"]
    PolyKalshi["Polymarket / Kalshi"] --> ScrapeSvc["scraping_service.py"]
    OpenAI["OpenAI API"] --> EmbedRepo["embedding_repository.py"]
    ElevenLabs["ElevenLabs Scribe v1"] --> AgentPanel["AgentPanel"]
    Cloudinary["Cloudinary"] --> MediaCfg["mediaConfig.ts"]
    GeminiAPI["Google Gemini API"] --> GeminiClient["gemini_client.py"]
```

**Database**
```mermaid
flowchart LR
    ContentTbl["content_table"] --> Sources["sources"]
    ContentTbl --> Engagement["engagement"]
    ContentTbl --> Entities["entities"]
    ContentTbl --> Events["event_relationships"]
```

---

## How It Works

World events are ingested from external sources (ACLED, Polymarket, Kalshi) and stored in a PostgreSQL database alongside AI-generated embeddings and engagement metrics. The FastAPI backend serves this data through a set of read-only routes that the React frontend consumes.

On load, the frontend plots every event as a node on an interactive 3D globe. Relationship arcs connect related events based on semantic similarity. Filters and a timeline slider let users slice the data without re-fetching — visibility is controlled client-side so the globe never resets.

Clicking an event node opens a detail panel. Two Gemini calls fire in the background: one scores the event's credibility, and another uses Google Search grounding to surface the latest developments framed through a Canada-impact lens.

The Argus AI agent accepts natural-language queries (typed or via voice). The backend retrieves the most relevant events from the database, expands the context through graph neighbors, and passes everything to Gemini to produce a structured answer with citations. The frontend turns those citations into clickable markers that animate the globe camera to the referenced event.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 19 + Vite 6 + TypeScript 5 |
| Globe | react-globe.gl (three.js) |
| Styling | Tailwind CSS 3 + CSS custom properties |
| Media | Cloudinary (images + video) with S3 and placeholder fallbacks |
| Backend framework | FastAPI + Uvicorn |
| Database | PostgreSQL with pgvector extension |
| AI inference | Google Gemini 2.5-flash |
| AI grounding | Gemini Google Search grounding tool |
| Embeddings | OpenAI text-embedding-3-small (vector 1536) |
| Voice input | ElevenLabs Scribe v1 (speech-to-text) |
| Market signals | Polymarket + Kalshi live scraping |
| External data | ACLED conflict event API |

---

## Project Structure

```
argus/
├── 001_init_schema.sql          # PostgreSQL schema (pgvector + pgcrypto)
├── frontend/
│   ├── public/
│   │   ├── countries.geojson    # GeoJSON hex-dot land layer for globe
│   │   └── placeholder-event.svg
│   └── src/
│       ├── main.tsx             # Entry; AppProvider > UserPersonaProvider > AgentProvider
│       ├── App.tsx              # Bootstrap: fetch points + arcs, build synthetic timeline
│       ├── index.css            # Design tokens (CSS variables) + Space Mono font
│       ├── api/
│       │   └── client.ts        # All typed fetch calls to FastAPI
│       ├── components/
│       │   ├── Globe/
│       │   │   └── GlobeView.tsx          # react-globe.gl; points, arcs, tooltips, clusters
│       │   ├── Filters/
│       │   │   └── FilterBar.tsx          # Event-type filter chips
│       │   ├── Timeline/
│       │   │   └── TimelineSlider.tsx     # Scrub + play/pause (150ms tick, 120 steps)
│       │   ├── Modal/
│       │   │   ├── EventModal.tsx         # Right slide-in event detail panel
│       │   │   └── RealTimeAnalysisSection.tsx  # Gemini + Search grounding block
│       │   └── Agent/
│       │       ├── AgentPanel.tsx         # Left slide-in; voice input; query submit
│       │       ├── AgentAnswerView.tsx    # Parsed citations, badges, financial impact
│       │       ├── AgentLauncherButton.tsx
│       │       ├── AgentNavigationOverlay.tsx   # Camera animation sequencer
│       │       ├── FinancialImpactSection.tsx
│       │       └── PersonaSelector.tsx
│       ├── context/
│       │   ├── AppContext.tsx             # Events, arcs, filters, timeline, autoSpin
│       │   ├── AgentContext.tsx           # Agent state, navigation plan, highlights
│       │   └── UserPersonaContext.tsx     # Role + industry
│       ├── types/
│       │   ├── events.ts                 # Event, ContentPoint, ContentArc, EventDetail…
│       │   └── agent.ts                  # AgentResponse, NavigationPlan, FinancialImpact…
│       └── utils/
│           └── mediaConfig.ts            # Cloudinary / S3 / placeholder URL resolver
└── backend/
    └── app/
        ├── main.py                        # FastAPI app, CORS, router registration
        ├── config.py                      # GEMINI_API_KEY, GEMINI_MODEL env vars
        ├── models/
        │   ├── enums.py                   # EventType, RelationshipType StrEnums
        │   ├── schemas.py                 # Core Pydantic response models
        │   └── agent_schemas.py           # Agent-specific Pydantic models
        ├── routers/
        │   ├── content.py                 # /content/* — points, arcs, detail, AI endpoints
        │   ├── agent.py                   # /agent/query
        │   ├── ingestion.py               # /ingestion/acled
        │   ├── embeddings.py              # /embeddings/backfill/content
        │   └── market_signals.py          # /market-signals
        ├── services/
        │   ├── agent_service.py           # Graph-RAG pipeline
        │   ├── agent_tools.py             # DB query tools (search, relate, detail, impact)
        │   ├── gemini_client.py           # Gemini client + structured prompting
        │   └── scraping_service.py        # Polymarket + Kalshi live fetch
        ├── repositories/
        │   └── content_repository.py      # Market signal row persistence
        ├── embeddings/
        │   ├── embedding_repository.py
        │   ├── embedding_backfill_service.py
        │   └── openai_embedding_client.py
        └── ingestion/
            ├── ingestion_service.py       # ACLED pipeline: fetch → normalize → dedupe → insert
            ├── content_repository.py      # ensure_sources, insert_content
            ├── db.py                      # asyncpg connection pool
            └── acled/
                ├── acled_client.py
                └── acled_normalizer.py
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with the `pgvector` and `pgcrypto` extensions enabled

### Database

```bash
# Apply schema
psql -U postgres -d your_db -f 001_init_schema.sql
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables (see table below)
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/argus
export GEMINI_API_KEY=your_gemini_key

uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env — add VITE_CLOUDINARY_CLOUD_NAME if you have one
npm run dev
```

App: http://localhost:5173

---

## Environment Variables

### Backend

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | asyncpg connection string to PostgreSQL |
| `GEMINI_API_KEY` | No | Google Gemini API key. Agent degrades gracefully without it. |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash` |
| `OPENAI_API_KEY` | No | Enables pgvector semantic search. Falls back to keyword search without it. |
| `ACLED_API_KEY` | No | Required only for `/ingestion/acled` |

### Frontend

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | No | FastAPI base URL. Defaults to `/api` (Vite proxy → `http://127.0.0.1:8000`) |
| `VITE_CLOUDINARY_CLOUD_NAME` | No | Enables Cloudinary image delivery. Falls back to placeholder SVG. |
| `VITE_ELEVENLABS_API_KEY` | No | Enables voice input in the agent panel via ElevenLabs Scribe v1. |

---

## AI Agent

The Argus AI agent is accessible via the panel in the top-right corner of the interface. Within it, you can query under various personas, receiving specific answers to your situation.

### Query Types

| Type | Example |
|---|---|
| `event_explanation` | "Why did the OPEC production cut happen?" |
| `impact_analysis` | "What is the financial impact of the Red Sea disruption on Canada?" |
| `connection_discovery` | "What events are related to semiconductor export controls?" |
| `entity_relevance` | "What does this mean for Canadian oil sands?" |

### Agent Pipeline (Graph-RAG)

```
User query
    │
    ▼
1. Query classification (keyword pattern matching)
    │
    ▼
2. Seed retrieval
   ├── Keyword ILIKE search against content_table
   └── pgvector cosine fallback (if OpenAI key present)
    │
    ▼
3. Two-hop graph expansion
   └── pgvector nearest neighbors for each seed article
    │
    ▼
4. Context assembly
   ├── Article bodies for seed events
   └── Financial impact heuristics (sector mapping + sentiment scoring)
    │
    ▼
5. Gemini 2.5-flash synthesis
   ├── Persona-aware system prompt
   ├── Inline [cite:UUID] citations enforced
   └── Structured JSON output:
       answer · confidence · query_type · caution_banner
       navigation_plan · highlight_relationships
       financial_impact · cited_event_map
    │
    ▼
6. Frontend rendering
   ├── Citation badges → globe navigation on click
   ├── AgentNavigationOverlay → camera animation
   └── Auto-open event modal at destination
```
