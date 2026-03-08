# Argus

**Argus** is a 3D global event intelligence dashboard that visualizes world events and explains why they matter to Canada. Named after the all-seeing giant of Greek mythology, Argus monitors the world and surfaces geopolitical, economic, climate, and policy events — connecting them to Canadian impact through an AI analysis layer.

---

## Architecture

```mermaid
flowchart TD
    subgraph Browser["Browser (React 19 + Vite 6 + TypeScript 5)"]
        direction TB
        App["App.tsx\nBootstrap + data fetch"]

        subgraph Contexts["React Context Layer"]
            AppCtx["AppContext\nevents · arcs · filters · timeline · autoSpin"]
            AgentCtx["AgentContext\nquery state · navigation plan · highlights"]
            PersonaCtx["UserPersonaContext\nrole · industry"]
        end

        subgraph UI["UI Components"]
            Globe["GlobeView\nreact-globe.gl\npoints · arcs · hover tooltips\ncluster popups · agent pulse rings"]
            FilterBar["FilterBar\nevent-type chips"]
            Timeline["TimelineSlider\nscrub + play/pause"]
            Modal["EventModal\nhero image · confidence badge\nreal-time analysis · related events\nsource cards · engagement snapshot"]
            Agent["AgentPanel\nArgus AI · voice input\npersona selector\nstructured answer view"]
            NavOverlay["AgentNavigationOverlay\ncamera animation sequencer"]
        end

        API["api/client.ts\ntyped fetch wrapper"]
        Media["mediaConfig.ts\nCloudinary / S3 / placeholder resolver"]
    end

    subgraph Backend["Backend (FastAPI + Python)"]
        direction TB
        Main["main.py\nCORS · router registration"]

        subgraph Routers["Routers"]
            Content["/content\npoints · arcs · detail\nconfidence · realtime-analysis"]
            AgentRouter["/agent\nquery"]
            Ingest["/ingestion\nacled"]
            Embed["/embeddings\nbackfill"]
            Market["/market-signals\npolymarket · kalshi"]
        end

        subgraph Services["Services"]
            AgentSvc["agent_service.py\nGraph-RAG pipeline\nquery classification → seed search\n→ vector expansion → Gemini synthesis"]
            GeminiClient["gemini_client.py\nGemini 2.5-flash\nconfidence scoring\nreal-time analysis\nGoogle Search grounding"]
            AgentTools["agent_tools.py\nsearch_events · get_related_events\nget_event_details · analyze_financial_impact\nweb_fallback_search"]
            ScrapeSvc["scraping_service.py\nlive Polymarket + Kalshi signals"]
            IngestSvc["ingestion_service.py\nACLED fetch → normalize → dedupe → insert"]
        end

        subgraph Repos["Repositories"]
            ContentRepo["content_repository.py\nmarket signal persistence"]
            EmbedRepo["embedding_repository.py\nOpenAI embedding store"]
            IngestRepo["ingestion/content_repository.py\nensure_sources · insert_content"]
        end
    end

    subgraph DB["Database (PostgreSQL + pgvector)"]
        direction LR
        ContentTbl["content_table\nid · title · body · url · published_at\nlatitude · longitude · event_type\nembedding vector(1536) · sentiment_score\nmarket_signal · image_url · s3_url"]
        Sources["sources\nname · type · base_url · trust_score"]
        Engagement["engagement\nreddit · twitter · polymarket metrics"]
        Entities["entities + content_entities\nnamed entity graph"]
        EventsTbl["events + event_relationships\n(schema ready, future cluster layer)"]
        ContentTbl --> Sources
        ContentTbl --> Engagement
        ContentTbl --> Entities
    end

    subgraph External["External Services"]
        Cloudinary["Cloudinary\nevent hero images + video"]
        GeminiAPI["Google Gemini API\ngemini-2.5-flash\nGoogle Search grounding tool"]
        OpenAIEmbed["OpenAI API\ntext-embedding-3-small\nvector(1536)"]
        ElevenLabs["ElevenLabs\nScribe v1 speech-to-text"]
        ACLEDApi["ACLED API\nconflict event data"]
        PolyKalshi["Polymarket / Kalshi\nprediction market signals"]
    end

    App --> API
    App --> Contexts
    Contexts --> UI
    UI --> API
    Media --> Cloudinary

    API -- "GET /content/points\nGET /content/arcs\nGET /content/{id}\nPOST /content/{id}/confidence-score\nPOST /content/{id}/realtime-analysis\nPOST /agent/query\nGET /market-signals" --> Main
    Main --> Routers
    Content --> AgentTools
    Content --> GeminiClient
    AgentRouter --> AgentSvc
    AgentSvc --> AgentTools
    AgentSvc --> GeminiClient
    Market --> ScrapeSvc
    Ingest --> IngestSvc
    Embed --> EmbedRepo

    AgentTools --> DB
    ContentRepo --> DB
    IngestRepo --> DB
    EmbedRepo --> DB

    GeminiClient --> GeminiAPI
    GeminiAPI --> GeminiAPI
    EmbedRepo --> OpenAIEmbed
    AgentTools -. "pgvector fallback" .-> OpenAIEmbed
    ScrapeSvc --> PolyKalshi
    IngestSvc --> ACLEDApi
    Agent -- "voice → text" --> ElevenLabs
```

---

## How It Works

### Data Layer
Raw article data lives in `content_table`. Each row is a scraped news article or event report with a geolocation, event type classification, optional OpenAI embedding (`vector(1536)`), and engagement metrics pulled from Reddit, Twitter, and prediction markets.

### Globe Rendering
On load, the frontend fetches all content points from the last 31 days and draws them as colored nodes on a `react-globe.gl` sphere. Canada is highlighted in red. Relationship arcs are computed server-side by an O(n²) cosine similarity pass over up to 200 items at the threshold of 0.4.

Visibility (filters, timeline) is handled entirely through `pointRadius` and `pointColor` accessor functions — the underlying data array is never mutated, preventing `react-globe.gl` from re-triggering enter animations.

### Event Modal
Clicking a node opens a right slide-in panel that fetches the full article detail. Two Gemini calls fire in the background:
1. **Confidence score** — rates the credibility of the event (0.0–1.0) using the article title, source, and event type.
2. **Real-time analysis** — uses Gemini with Google Search grounding to pull the latest developments and frame them through a Canada-impact lens.

Results are module-level cached per event ID to avoid redundant API calls during a session.

### Argus AI Agent
The agent panel accepts natural-language queries (typed or voice via ElevenLabs Scribe). The backend runs a **Graph-RAG** pipeline:
1. Classify query type (impact analysis, connection discovery, entity relevance, event explanation).
2. Seed retrieval via keyword `ILIKE` search, falling back to pgvector cosine distance if OpenAI embeddings are available.
3. Two-hop graph expansion: fetch vector neighbors of every seed article.
4. Gemini 2.5-flash synthesizes the full context into a structured JSON response with inline `[cite:UUID]` citations, a confidence level, a globe navigation plan, and an optional financial impact block.

The frontend parses citations into clickable reference badges. The `AgentNavigationOverlay` component reads the navigation plan and drives a sequenced camera animation — panning to each relevant event, auto-opening the modal on arrival.

### Persona System
Both the agent and the modal's real-time analysis accept a user role (investor, policymaker, researcher, journalist, general) and an industry. The backend injects a persona suffix into the Gemini system prompt, causing responses to frame Canada-impact through the user's lens.

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

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/content/points` | All geolocated articles from the last 31 days |
| `GET` | `/content/arcs` | Cosine similarity arc pairs (`?threshold=0.4`) |
| `GET` | `/content/{id}` | Full article detail: title, body, sources, engagement, entities |
| `POST` | `/content/{id}/confidence-score` | Gemini credibility rating (0.0–1.0) |
| `POST` | `/content/{id}/realtime-analysis` | Gemini + Google Search latest developments |
| `POST` | `/agent/query` | Full Graph-RAG agent: classify → retrieve → expand → Gemini synthesis |
| `GET` | `/market-signals` | Live Polymarket + Kalshi prediction market data |
| `POST` | `/ingestion/acled` | Trigger ACLED conflict event ingestion |
| `POST` | `/embeddings/backfill/content` | Backfill OpenAI embeddings for unembedded rows |

---

## Event Types

| Type | Color | Description |
|---|---|---|
| `geopolitics` | Red | Military conflicts, diplomatic tensions, sanctions |
| `trade_supply_chain` | Orange | Port disruptions, shipping lanes, logistics |
| `energy_commodities` | Yellow | Oil, gas, potash, critical minerals |
| `financial_markets` | Green | Central bank decisions, currencies, equity markets |
| `climate_disasters` | Blue | Wildfires, floods, extreme weather events |
| `policy_regulation` | Purple | Legislation, trade rules, international agreements |

## Relationship Types

| Type | Description |
|---|---|
| `market_reaction` | One event caused a market response in another |
| `commodity_link` | Events share underlying commodity exposure |
| `supply_chain_link` | Events affect the same supply chain node |
| `regional_spillover` | Geographic proximity causes cross-border effects |
| `policy_impact` | A policy change cascades into a real-world event |
| `same_event_family` | Events are part of the same broader crisis |

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

The Argus AI agent is accessible via the panel in the top-right corner of the interface.

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

### Voice Input

With `VITE_ELEVENLABS_API_KEY` set, the agent panel supports push-to-talk:
- Click the microphone button **or** hold `Shift` (when the text input is not focused)
- Recording auto-stops after 3 seconds of silence (Web Audio API RMS threshold < 8)
- Audio is sent to ElevenLabs Scribe v1 and the transcript is populated into the query box

---

## Design System

All colors, spacing, and typography are defined as CSS custom properties in `src/index.css`. The palette is monochromatic dark with a single red accent for Canada. The typeface throughout is **Space Mono** (monospace), reinforcing the intelligence-terminal aesthetic.

The globe auto-spins on load. Any user interaction (filter click, timeline scrub, node click, agent query) stops the spin and starts a 5-minute inactivity timer that re-enables it.
