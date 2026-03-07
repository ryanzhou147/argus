from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import agent, events, filters, timeline

app = FastAPI(
    title="Global Event Intelligence API",
    description="Read-only API serving global events and their impact on Canada.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(filters.router)
app.include_router(timeline.router)
app.include_router(agent.router)


@app.get("/health")
def health():
    return {"status": "ok"}
