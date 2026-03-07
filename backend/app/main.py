from dotenv import load_dotenv

load_dotenv()  # Load .env so DATABASE_URL is available for scraper persist

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import events, filters, market_signals, timeline

app = FastAPI(
    title="Global Event Intelligence API",
    description="Read-only API serving global events and their impact on Canada.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(filters.router)
app.include_router(market_signals.router)
app.include_router(timeline.router)


@app.get("/health")
def health():
    return {"status": "ok"}
