"""
geocode_events.py
=================
Scans the AWS PostgreSQL database for events and content_table rows that are
missing latitude / longitude and uses the Chutes AI API to infer coordinates
from the available event data.

Tables updated:
  - events         (primary_latitude, primary_longitude)
  - content_table  (latitude, longitude)

Schema (from 001_init_schema.sql):
  events.primary_latitude  FLOAT
  events.primary_longitude FLOAT
  content_table.latitude   FLOAT
  content_table.longitude  FLOAT

Usage:
    python -m backend.app.services.geocode_events
    python -m backend.app.services.geocode_events --dry-run
    python -m backend.app.services.geocode_events --table events
    python -m backend.app.services.geocode_events --table content_table
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Env / config
# ---------------------------------------------------------------------------

_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

CHUTES_URL = "https://llm.chutes.ai/v1/chat/completions"
CHUTES_MODEL = "default"

RETRY_DELAY = 2      # seconds between Chutes retries
MAX_RETRIES = 3
REQUEST_TIMEOUT = 45  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database connection (psycopg2 → AWS PostgreSQL)
# ---------------------------------------------------------------------------

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "psycopg2-binary is required. Run: pip install psycopg2-binary"
    ) from exc


def _build_dsn() -> str:
    """Build a DSN from individual PG_* env vars or fall back to DATABASE_URL."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url
    host = os.environ.get("PG_HOST")
    port = os.environ.get("PG_PORT", "5432")
    user = os.environ.get("PG_USER")
    password = os.environ.get("PG_PASSWORD")
    dbname = os.environ.get("PG_DB", "postgres")
    if not (host and user and password):
        raise ValueError(
            "Database credentials missing. Set DATABASE_URL or PG_HOST / PG_USER / PG_PASSWORD in .env"
        )
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@contextmanager
def get_cursor() -> Generator:
    dsn = _build_dsn()
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Chutes AI geocoding
# ---------------------------------------------------------------------------

def _load_api_key() -> str:
    api_key = os.environ.get("CHUTES_API_KEY", "").strip()
    if not api_key:
        raise ValueError("CHUTES_API_KEY not set in .env")
    return api_key


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def _call_chutes(api_key: str, prompt: str) -> str:
    """Call Chutes chat completions and return the raw assistant text."""
    for attempt in range(1, MAX_RETRIES + 1):
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
                    "max_tokens": 1024,
                    "temperature": 0.3,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            log.warning("Chutes attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise RuntimeError("Chutes API failed after all retries")


def geocode_via_ai(api_key: str, context: dict) -> tuple[float, float] | None:
    """
    Ask Chutes to infer (latitude, longitude) from event context fields.
    Returns (lat, lon) floats or None if inference fails.

    context keys used (all optional, any can be None/empty):
        title, summary, canada_impact_summary, event_type, start_time
    """
    title = context.get("title") or ""
    summary = context.get("summary") or ""
    impact = context.get("canada_impact_summary") or ""
    event_type = context.get("event_type") or ""
    start_time = context.get("start_time") or ""
    body = context.get("body") or ""

    # Build a concise context block — include only non-empty fields
    lines = []
    if title:
        lines.append(f"Title: {title}")
    if event_type:
        lines.append(f"Event type: {event_type}")
    if start_time:
        lines.append(f"Date: {str(start_time)[:10]}")
    if summary:
        lines.append(f"Summary: {summary[:400]}")
    if body and body != summary:
        lines.append(f"Body: {body[:400]}")
    if impact:
        lines.append(f"Canada impact: {impact[:300]}")

    if not lines:
        log.debug("No context available for geocoding — skipping")
        return None

    context_block = "\n".join(lines)

    prompt = (
        "You are a geocoding assistant. Based ONLY on the event information below, "
        "determine the most likely primary geographic location (the main place where "
        "this event occurred or originates from) and return its coordinates.\n\n"
        f"{context_block}\n\n"
        "Respond with ONLY a valid JSON object in this exact format:\n"
        '{"latitude": <float>, "longitude": <float>}\n'
        "Use decimal degrees. Do not include any explanation, markdown, or extra text."
    )

    try:
        raw = _call_chutes(api_key, prompt)
        raw = _strip_think_tags(raw)

        if not raw:
            log.warning("Chutes returned empty response after stripping think tags")
            return None

        # --- Attempt 1: well-formed JSON object ---
        match = re.search(r'\{[^{}]*"latitude"[^{}]*"longitude"[^{}]*\}', raw)
        if not match:
            match = re.search(r'\{[^{}]*"longitude"[^{}]*"latitude"[^{}]*\}', raw)
        if match:
            try:
                data = json.loads(match.group())
                lat = float(data["latitude"])
                lon = float(data["longitude"])
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    return lat, lon
            except (json.JSONDecodeError, KeyError, ValueError):
                pass  # fall through to next attempt

        # --- Attempt 2: extract floats next to "latitude" / "longitude" keys ---
        lat_match = re.search(r'"latitude"\s*:\s*(-?\d+(?:\.\d+)?)', raw)
        lon_match = re.search(r'"longitude"\s*:\s*(-?\d+(?:\.\d+)?)', raw)
        if lat_match and lon_match:
            lat = float(lat_match.group(1))
            lon = float(lon_match.group(1))
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return lat, lon

        log.warning("No parseable coordinates in Chutes response: %r", raw[:300])
        return None
    except Exception as exc:
        log.warning("Failed to parse geocoding response: %s", exc)
        return None


# ---------------------------------------------------------------------------
# events table
# ---------------------------------------------------------------------------

def fetch_events_missing_coords(cur) -> list[dict]:
    """Return all events rows where primary_latitude or primary_longitude is NULL."""
    cur.execute(
        """
        SELECT id, title, summary, event_type, canada_impact_summary, start_time
        FROM events
        WHERE primary_latitude IS NULL AND primary_longitude IS NULL
        ORDER BY start_time DESC NULLS LAST
        """
    )
    return [dict(row) for row in cur.fetchall()]


def update_event_coords(cur, event_id: str, lat: float, lon: float) -> None:
    cur.execute(
        """
        UPDATE events
        SET primary_latitude = %s, primary_longitude = %s
        WHERE id = %s
        """,
        (lat, lon, event_id),
    )


def process_events_table(api_key: str, dry_run: bool = False) -> dict:
    stats = {"total": 0, "updated": 0, "skipped": 0, "failed": 0}

    with get_cursor() as cur:
        rows = fetch_events_missing_coords(cur)
        stats["total"] = len(rows)
        log.info("events: %d rows missing coordinates", len(rows))

        for row in rows:
            row_id = str(row["id"])
            log.info("Geocoding event %s — %s", row_id, row.get("title", "")[:80])
            coords = geocode_via_ai(api_key, row)
            if coords is None:
                log.warning("  -> Could not geocode event %s, skipping", row_id)
                stats["failed"] += 1
                continue
            lat, lon = coords
            log.info("  -> lat=%.4f  lon=%.4f", lat, lon)
            if not dry_run:
                update_event_coords(cur, row_id, lat, lon)
                stats["updated"] += 1
            else:
                log.info("  [dry-run] would update event %s", row_id)
                stats["skipped"] += 1

    return stats


# ---------------------------------------------------------------------------
# content_table
# ---------------------------------------------------------------------------

def fetch_content_missing_coords(cur) -> list[dict]:
    """Return all content_table rows where latitude or longitude is NULL."""
    cur.execute(
        """
        SELECT id, title, body, event_type, published_at
        FROM content_table
        WHERE latitude IS NULL AND longitude IS NULL
        ORDER BY published_at DESC NULLS LAST
        """
    )
    return [dict(row) for row in cur.fetchall()]


def update_content_coords(cur, content_id: str, lat: float, lon: float) -> None:
    cur.execute(
        """
        UPDATE content_table
        SET latitude = %s, longitude = %s
        WHERE id = %s
        """,
        (lat, lon, content_id),
    )


def process_content_table(api_key: str, dry_run: bool = False) -> dict:
    stats = {"total": 0, "updated": 0, "skipped": 0, "failed": 0}

    with get_cursor() as cur:
        rows = fetch_content_missing_coords(cur)
        stats["total"] = len(rows)
        log.info("content_table: %d rows missing coordinates", len(rows))

        for row in rows:
            row_id = str(row["id"])
            log.info("Geocoding content %s — %s", row_id, row.get("title", "")[:80])
            # Map content_table columns to the geocode_via_ai context keys
            context = {
                "title": row.get("title"),
                "summary": row.get("body"),
                "body": row.get("body"),
                "event_type": row.get("event_type"),
                "start_time": row.get("published_at"),
            }
            coords = geocode_via_ai(api_key, context)
            if coords is None:
                log.warning("  -> Could not geocode content %s, skipping", row_id)
                stats["failed"] += 1
                continue
            lat, lon = coords
            log.info("  -> lat=%.4f  lon=%.4f", lat, lon)
            if not dry_run:
                update_content_coords(cur, row_id, lat, lon)
                stats["updated"] += 1
            else:
                log.info("  [dry-run] would update content %s", row_id)
                stats["skipped"] += 1

    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill missing lat/lon in AWS PostgreSQL using Chutes AI."
    )
    parser.add_argument(
        "--table",
        choices=["events", "content_table", "both"],
        default="both",
        help="Which table to process (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without writing to the database",
    )
    args = parser.parse_args()

    api_key = _load_api_key()

    if args.table in ("events", "both"):
        stats = process_events_table(api_key, dry_run=args.dry_run)
        log.info(
            "events table — total=%d updated=%d skipped=%d failed=%d",
            stats["total"], stats["updated"], stats["skipped"], stats["failed"],
        )

    if args.table in ("content_table", "both"):
        stats = process_content_table(api_key, dry_run=args.dry_run)
        log.info(
            "content_table — total=%d updated=%d skipped=%d failed=%d",
            stats["total"], stats["updated"], stats["skipped"], stats["failed"],
        )


if __name__ == "__main__":
    main()
