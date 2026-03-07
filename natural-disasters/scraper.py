"""
EONET Natural Disasters Scraper
================================
Fetches events from NASA EONET API v2.1 for the last 14 days and persists
them into a local SQLite database matching the production schema.

All scraped events default to event_type = "climate_disasters".

Usage:
    python scraper.py              # scrape last 14 days (default)
    python scraper.py --days 7     # scrape last 7 days
    python scraper.py --status all # include closed events too
"""
import argparse
import logging
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests

from db import get_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

EONET_BASE = "https://eonet.gsfc.nasa.gov/api/v2.1"
DEFAULT_EVENT_TYPE = "climate_disasters"
DEFAULT_CONFIDENCE = 0.75

_ENV_PATH = Path(__file__).parent / ".env"


CHUTES_URL = "https://llm.chutes.ai/v1/chat/completions"
CHUTES_MODEL = "default"


def _load_api_key() -> str:
    """Load Chutes API key from .env."""
    if not _ENV_PATH.exists():
        raise FileNotFoundError(f".env not found at {_ENV_PATH}.")
    raw = _ENV_PATH.read_text(encoding="utf-8").strip()
    # Support both raw key and KEY=VALUE format
    api_key = raw.split("=", 1)[1].strip() if "=" in raw else raw
    if not api_key:
        raise ValueError("No API key found in .env file.")
    return api_key


def generate_body(api_key: str, title: str, categories: list[str],
                  lat: float | None, lon: float | None, start_time: str | None) -> str:
    """Call Chutes to generate a 2-3 sentence event description for the body field."""
    location_hint = f"at coordinates ({lat:.2f}, {lon:.2f})" if lat and lon else "at an unspecified location"
    date_hint = f"on {start_time[:10]}" if start_time else "recently"
    category_str = ", ".join(categories) if categories else "natural disaster"

    prompt = (
        f"Write 2-3 concise factual sentences describing this natural disaster event "
        f"for a global event intelligence platform. Do not include a header or title. "
        f"Just the description paragraph.\n\n"
        f"Event: {title}\n"
        f"Type: {category_str}\n"
        f"Location: {location_hint}\n"
        f"Date: {date_hint}"
    )

    try:
        resp = requests.post(
            CHUTES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": CHUTES_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.4,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        # Strip complete <think>...</think> blocks
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        # Strip incomplete <think> blocks (truncated response, no closing tag)
        content = re.sub(r"<think>.*", "", content, flags=re.DOTALL)
        return content.strip()
    except Exception as exc:
        log.warning("Chutes call failed for '%s': %s", title, exc)
        return f"Natural disaster event ({category_str}): {title}."


# ---------------------------------------------------------------------------
# EONET API helpers
# ---------------------------------------------------------------------------

def fetch_events(days: int = 14, status: str | None = None) -> list[dict]:
    """
    Fetch events from the EONET events endpoint.

    Args:
        days:   Number of prior days to retrieve (including today).
        status: "open", "closed", or None (returns only open events when omitted).
    """
    params: dict = {"days": days}
    if status:
        params["status"] = status

    url = f"{EONET_BASE}/events"
    log.info("Fetching EONET events: %s params=%s", url, params)

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    events = data.get("events", [])
    log.info("Received %d events from EONET", len(events))
    return events


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

def _first_geometry(geometries: list[dict]) -> dict | None:
    return geometries[0] if geometries else None


def _last_geometry(geometries: list[dict]) -> dict | None:
    return geometries[-1] if geometries else None


def _parse_date(date_str: str | None) -> str | None:
    """Normalise ISO-8601 date strings; returns None if input is falsy."""
    if not date_str:
        return None
    # Already ISO-8601; strip trailing Z for SQLite compatibility
    return date_str.replace("Z", "+00:00") if date_str.endswith("Z") else date_str


def _coordinates(geometry: dict | None) -> tuple[float | None, float | None]:
    """Return (latitude, longitude) from a GeoJSON geometry dict."""
    if not geometry:
        return None, None
    coords = geometry.get("coordinates")
    if not coords:
        return None, None
    # GeoJSON: [longitude, latitude]
    if geometry.get("type") == "Point":
        return float(coords[1]), float(coords[0])
    if geometry.get("type") == "Polygon":
        # Use centroid of the first ring
        ring = coords[0]
        lats = [p[1] for p in ring]
        lons = [p[0] for p in ring]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    return None, None


def _derive_source_base_url(source_url: str) -> str:
    """Extract scheme + host from a URL."""
    parsed = urlparse(source_url)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else source_url


# ---------------------------------------------------------------------------
# Database upsert helpers
# ---------------------------------------------------------------------------

def upsert_source(conn, source_id: str, source_url: str) -> int:
    """
    Insert or ignore a source row. Returns the rowid for the source.
    source_id from EONET (e.g. "InciWeb") is used as the name.
    """
    base_url = _derive_source_base_url(source_url)
    conn.execute(
        """
        INSERT INTO sources (name, type, base_url, trust_score)
        VALUES (?, 'api', ?, 0.8)
        ON CONFLICT(name) DO NOTHING
        """,
        (source_id, base_url),
    )
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (source_id,)).fetchone()
    return row["id"]


def upsert_content_item(
    conn,
    *,
    source_db_id: int,
    title: str,
    body: str | None,
    url: str,
    published_at: str | None,
    latitude: float | None,
    longitude: float | None,
) -> str:
    """
    Insert a content_table row. Returns the content item UUID.
    Skips insert if URL already exists and returns existing id.
    """
    existing = conn.execute(
        "SELECT id FROM content_table WHERE url = ?", (url,)
    ).fetchone()
    if existing:
        return existing["id"]

    item_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO content_table
            (id, source_id, title, body, url, published_at,
             latitude, longitude, event_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            source_db_id,
            title,
            body,
            url,
            published_at,
            latitude,
            longitude,
            DEFAULT_EVENT_TYPE,
        ),
    )
    return item_id


def upsert_event(conn, eonet_event: dict) -> tuple[str, bool]:
    """
    Map one EONET event to the events table.
    Returns (event_uuid, is_new) where is_new=False means it already existed.
    """
    eonet_id: str = eonet_event["id"]
    existing = conn.execute(
        "SELECT id FROM events WHERE eonet_id = ?", (eonet_id,)
    ).fetchone()
    if existing:
        log.debug("Event already exists: %s", eonet_id)
        return existing["id"], False

    geometries: list[dict] = eonet_event.get("geometries", [])
    first_geom = _first_geometry(geometries)
    last_geom = _last_geometry(geometries)

    lat, lon = _coordinates(first_geom)
    start_time = _parse_date(first_geom.get("date") if first_geom else None)
    # end_time: use `closed` field if present, else last geometry date
    closed = _parse_date(eonet_event.get("closed"))
    end_time = closed or _parse_date(last_geom.get("date") if last_geom and last_geom != first_geom else None)

    title: str = eonet_event.get("title", "").strip()
    categories: list[dict] = eonet_event.get("categories", [])
    category_names = ", ".join(c.get("title", "") for c in categories)
    summary = f"Natural disaster event: {category_names}" if category_names else title

    event_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO events
            (id, title, summary, event_type, primary_latitude, primary_longitude,
             start_time, end_time, confidence_score, eonet_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            title,
            summary,
            DEFAULT_EVENT_TYPE,
            lat,
            lon,
            start_time,
            end_time,
            DEFAULT_CONFIDENCE,
            eonet_id,
        ),
    )
    log.debug("Inserted event %s (%s)", eonet_id, title)
    return event_id, True


def link_event_content(conn, event_id: str, content_item_id: str) -> None:
    conn.execute(
        """
        INSERT INTO event_content (event_id, content_item_id)
        VALUES (?, ?)
        ON CONFLICT DO NOTHING
        """,
        (event_id, content_item_id),
    )


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_events(eonet_events: list[dict], api_key: str) -> dict:
    """Persist all EONET events and their sources into SQLite."""
    stats = {"events_new": 0, "events_skipped": 0, "content_items": 0}

    conn = get_connection()
    with conn:
        for i, eonet_event in enumerate(eonet_events):
            event_id, is_new = upsert_event(conn, eonet_event)

            if is_new:
                stats["events_new"] += 1
            else:
                stats["events_skipped"] += 1
                continue

            geometries: list[dict] = eonet_event.get("geometries", [])
            sources: list[dict] = eonet_event.get("sources", [])
            title: str = eonet_event.get("title", "")
            categories: list[str] = [c.get("title", "") for c in eonet_event.get("categories", [])]

            first_geom = _first_geometry(geometries)
            lat, lon = _coordinates(first_geom)
            published_at = _parse_date(first_geom.get("date") if first_geom else None)

            # Generate AI body description
            log.info("[%d/%d] Generating description for: %s", i + 1, len(eonet_events), title)
            body = generate_body(api_key, title, categories, lat, lon, published_at)

            # Also store AI description as events.summary
            conn.execute(
                "UPDATE events SET summary = ? WHERE id = ?",
                (body, event_id),
            )

            # Use the EONET event link as a canonical content item if no sources
            canonical_sources = sources if sources else [
                {"id": "EONET", "url": eonet_event.get("link", "")}
            ]

            for src in canonical_sources:
                src_name: str = src.get("id", "EONET")
                src_url: str = src.get("url", "")
                if not src_url:
                    continue

                source_db_id = upsert_source(conn, src_name, src_url)
                content_id = upsert_content_item(
                    conn,
                    source_db_id=source_db_id,
                    title=title,
                    body=body,
                    url=src_url,
                    published_at=published_at,
                    latitude=lat,
                    longitude=lon,
                )
                link_event_content(conn, event_id, content_id)
                stats["content_items"] += 1

    conn.close()
    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape NASA EONET natural disaster events")
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of prior days to fetch (default: 14)",
    )
    parser.add_argument(
        "--status",
        choices=["open", "closed", "all"],
        default="all",
        help="Event status filter: open | closed | all (default: all)",
    )
    args = parser.parse_args()

    status_param = None if args.status == "all" else args.status

    log.info("Initialising database...")
    init_db()

    log.info("Loading Chutes API key...")
    api_key = _load_api_key()

    log.info("Fetching EONET events for last %d days (status=%s)...", args.days, args.status)
    eonet_events = fetch_events(days=args.days, status=status_param)

    log.info("Ingesting %d events (with AI descriptions)...", len(eonet_events))
    stats = ingest_events(eonet_events, api_key)

    log.info(
        "Done. new_events=%d skipped=%d content_items=%d",
        stats["events_new"],
        stats["events_skipped"],
        stats["content_items"],
    )


if __name__ == "__main__":
    main()
