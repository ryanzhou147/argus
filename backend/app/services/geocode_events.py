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
    python -m app.services.geocode_events
    python -m app.services.geocode_events --workers 10
    python -m app.services.geocode_events --dry-run
    python -m app.services.geocode_events --table events --workers 5
    python -m app.services.geocode_events --table content_table --workers 20
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

RETRY_DELAY = 2       # seconds between Chutes retries
MAX_RETRIES = 3
REQUEST_TIMEOUT = 45  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database connection (psycopg2 → AWS PostgreSQL)
# Each worker opens its own connection — psycopg2 connections are not thread-safe.
# ---------------------------------------------------------------------------

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "psycopg2-binary is required. Run: pip install psycopg2-binary"
    ) from exc


def _build_dsn() -> str:
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
            "Database credentials missing. Set DATABASE_URL or "
            "PG_HOST / PG_USER / PG_PASSWORD in .env"
        )
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@contextmanager
def get_cursor() -> Generator:
    """Open a short-lived connection and yield a RealDictCursor."""
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
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def _call_chutes(api_key: str, prompt: str) -> str:
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
    """
    title = context.get("title") or ""
    summary = context.get("summary") or ""
    impact = context.get("canada_impact_summary") or ""
    event_type = context.get("event_type") or ""
    start_time = context.get("start_time") or ""
    body = context.get("body") or ""

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

        # Attempt 1: well-formed JSON object
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
                pass

        # Attempt 2: extract floats directly after "latitude" / "longitude" keys
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
# Thread-safe stats counter
# ---------------------------------------------------------------------------

class _Stats:
    def __init__(self, total: int) -> None:
        self.total = total
        self.updated = 0
        self.failed = 0
        self.skipped = 0
        self._lock = threading.Lock()
        self._done = 0

    def record(self, outcome: str) -> int:
        """Increment outcome counter and return current done count."""
        with self._lock:
            self._done += 1
            if outcome == "updated":
                self.updated += 1
            elif outcome == "failed":
                self.failed += 1
            elif outcome == "skipped":
                self.skipped += 1
            return self._done

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
        }


# ---------------------------------------------------------------------------
# Per-row worker functions (each opens its own DB connection)
# ---------------------------------------------------------------------------

def _process_event_row(row: dict, api_key: str, dry_run: bool) -> str:
    """Geocode one events row and write result. Returns outcome string."""
    row_id = str(row["id"])
    log.info("Geocoding event %s — %s", row_id, (row.get("title") or "")[:80])

    coords = geocode_via_ai(api_key, row)
    if coords is None:
        log.warning("  -> Could not geocode event %s, skipping", row_id)
        return "failed"

    lat, lon = coords
    log.info("  -> [event] lat=%.4f  lon=%.4f  (%s)", lat, lon, row_id)

    if dry_run:
        log.info("  [dry-run] would update event %s", row_id)
        return "skipped"

    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET primary_latitude = %s, primary_longitude = %s
            WHERE id = %s
              AND primary_latitude IS NULL
              AND primary_longitude IS NULL
            """,
            (lat, lon, row_id),
        )
    return "updated"


def _process_content_row(row: dict, api_key: str, dry_run: bool) -> str:
    """Geocode one content_table row and write result. Returns outcome string."""
    row_id = str(row["id"])
    log.info("Geocoding content %s — %s", row_id, (row.get("title") or "")[:80])

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
        return "failed"

    lat, lon = coords
    log.info("  -> [content] lat=%.4f  lon=%.4f  (%s)", lat, lon, row_id)

    if dry_run:
        log.info("  [dry-run] would update content %s", row_id)
        return "skipped"

    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE content_table
            SET latitude = %s, longitude = %s
            WHERE id = %s
              AND latitude IS NULL
              AND longitude IS NULL
            """,
            (lat, lon, row_id),
        )
    return "updated"


# ---------------------------------------------------------------------------
# Orchestrators
# ---------------------------------------------------------------------------

def process_events_table(api_key: str, dry_run: bool = False, workers: int = 1) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, title, summary, event_type, canada_impact_summary, start_time
            FROM events
            WHERE primary_latitude IS NULL AND primary_longitude IS NULL
            ORDER BY start_time DESC NULLS LAST
            """
        )
        rows = [dict(r) for r in cur.fetchall()]

    stats = _Stats(len(rows))
    log.info("events: %d rows missing coordinates — using %d worker(s)", len(rows), workers)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_process_event_row, row, api_key, dry_run): row
            for row in rows
        }
        for future in as_completed(futures):
            try:
                outcome = future.result()
            except Exception as exc:
                log.error("Worker exception: %s", exc)
                outcome = "failed"
            done = stats.record(outcome)
            if done % 50 == 0 or done == stats.total:
                log.info(
                    "events progress: %d/%d  updated=%d failed=%d skipped=%d",
                    done, stats.total, stats.updated, stats.failed, stats.skipped,
                )

    return stats.as_dict()


def process_content_table(api_key: str, dry_run: bool = False, workers: int = 1) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, title, body, event_type, published_at
            FROM content_table
            WHERE latitude IS NULL AND longitude IS NULL
            ORDER BY published_at DESC NULLS LAST
            """
        )
        rows = [dict(r) for r in cur.fetchall()]

    stats = _Stats(len(rows))
    log.info("content_table: %d rows missing coordinates — using %d worker(s)", len(rows), workers)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_process_content_row, row, api_key, dry_run): row
            for row in rows
        }
        for future in as_completed(futures):
            try:
                outcome = future.result()
            except Exception as exc:
                log.error("Worker exception: %s", exc)
                outcome = "failed"
            done = stats.record(outcome)
            if done % 50 == 0 or done == stats.total:
                log.info(
                    "content_table progress: %d/%d  updated=%d failed=%d skipped=%d",
                    done, stats.total, stats.updated, stats.failed, stats.skipped,
                )

    return stats.as_dict()


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
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without writing to the database",
    )
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    api_key = _load_api_key()

    if args.table in ("events", "both"):
        stats = process_events_table(api_key, dry_run=args.dry_run, workers=args.workers)
        log.info(
            "events table done — total=%d updated=%d skipped=%d failed=%d",
            stats["total"], stats["updated"], stats["skipped"], stats["failed"],
        )

    if args.table in ("content_table", "both"):
        stats = process_content_table(api_key, dry_run=args.dry_run, workers=args.workers)
        log.info(
            "content_table done — total=%d updated=%d skipped=%d failed=%d",
            stats["total"], stats["updated"], stats["skipped"], stats["failed"],
        )


if __name__ == "__main__":
    main()
