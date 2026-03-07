"""
WHO Disease Outbreak News scraper for global event intelligence platform.
Fetches from https://www.who.int/api/news/diseaseoutbreaknews
No Playwright needed — full content returned by API.
Uploads hero images to S3 (WHO DON pages don't have structured images; skipped).
Writes to PostgreSQL.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WHO_URL     = "https://www.who.int/api/news/diseaseoutbreaknews"
WHO_BASE    = "https://www.who.int"
SF_CULTURE  = "en"
PAGE_SIZE   = 20

DATABASE_URL = os.environ["DATABASE_URL"]

# ---------------------------------------------------------------------------
# HTML → plain text
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    p = _HTMLStripper()
    p.feed(html)
    return p.get_text()


# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

_EVENT_KEYWORDS: dict[str, list[str]] = {
    "geopolitics": [
        "war", "conflict", "military", "sanction", "nato", "invasion", "election",
        "government", "coup", "protest",
    ],
    "trade_supply_chain": [
        "trade", "tariff", "supply chain", "export", "import", "logistics", "shipping",
    ],
    "energy_commodities": [
        "oil", "gas", "opec", "energy", "pipeline", "coal", "nuclear", "commodity",
    ],
    "financial_markets": [
        "stock", "market", "interest rate", "inflation", "recession", "gdp", "bank",
    ],
    "climate_disasters": [
        "climate", "hurricane", "earthquake", "flood", "wildfire", "drought", "disaster",
        "storm", "emissions", "heatwave",
    ],
    "policy_regulation": [
        "regulation", "legislation", "law", "policy", "bill", "parliament", "court",
        "ruling", "ban", "tax",
    ],
}


def classify_event_type(text: str) -> str:
    text_lower = text.lower()
    scores = {t: sum(kw in text_lower for kw in kws) for t, kws in _EVENT_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    # WHO content is almost always a disease/health topic; default to geopolitics
    # only if no keywords match at all — otherwise use best match
    return best if scores[best] > 0 else "geopolitics"


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

async def load_checkpoint(pool, key: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT checkpoint FROM scraper_checkpoints WHERE scraper = $1", key
        )
        return int(row["checkpoint"]) if row else 0


async def save_checkpoint(pool, key: str, skip: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scraper_checkpoints (scraper, checkpoint, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (scraper) DO UPDATE
                SET checkpoint = EXCLUDED.checkpoint, updated_at = NOW()
            """,
            key, str(skip),
        )


# ---------------------------------------------------------------------------
# WHO API fetch
# ---------------------------------------------------------------------------

async def fetch_outbreaks(client: httpx.AsyncClient, skip: int = 0) -> list[dict]:
    params = {
        "sf_culture":  SF_CULTURE,
        "$top":        PAGE_SIZE,
        "$skip":       skip,
        "$orderby":    "PublicationDate desc",
    }
    try:
        r = await client.get(WHO_URL, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("value", [])
    except Exception as e:
        print(f"[ERROR] WHO API: {e}")
        return []


# ---------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------

WHO_SOURCE = {
    "name":        "WHO Disease Outbreak News",
    "type":        "health",
    "base_url":    "https://www.who.int",
    "trust_score": 1.0,
}


async def ensure_who_source(pool) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sources (name, type, base_url, trust_score)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (name) DO UPDATE
                SET base_url    = EXCLUDED.base_url,
                    trust_score = EXCLUDED.trust_score
            RETURNING id
            """,
            WHO_SOURCE["name"],
            WHO_SOURCE["type"],
            WHO_SOURCE["base_url"],
            WHO_SOURCE["trust_score"],
        )
        return row["id"]


async def upsert_outbreak(conn, item: dict, source_id: int, event_type: str) -> str | None:
    don_id   = item.get("DonId", "")
    url      = f"{WHO_BASE}/{don_id}" if don_id else ""
    title    = item.get("Title", "")

    # Build body from available rich-text fields
    parts = [
        _strip_html(item.get("Overview")),
        _strip_html(item.get("Epidemiology")),
        _strip_html(item.get("Assessment")),
        _strip_html(item.get("Response")),
        _strip_html(item.get("Advice")),
        _strip_html(item.get("Summary")),
    ]
    body = " ".join(p for p in parts if p)

    pub_str = item.get("PublicationDate") or item.get("DateCreated")
    dt = None
    if pub_str:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(pub_str, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

    if not url or not title:
        return None

    try:
        row = await conn.fetchrow(
            """
            INSERT INTO content_table
                (source_id, title, body, url, published_at, image_url, event_type)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            source_id, title, body, url, dt, None, event_type,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[ERROR] DB insert failed ({url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

def print_outbreak(item: dict, event_type: str, db_id: str | None, dry_run: bool) -> None:
    status = "dry run" if dry_run else (f"inserted {db_id}" if db_id else "duplicate")
    don_id = item.get("DonId", "")
    body_preview = _strip_html(item.get("Overview") or item.get("Summary"))[:300].replace("\n", " ")
    print("=" * 60)
    print(f"DON ID:     {don_id}")
    print(f"TITLE:      {item.get('Title', '')}")
    print(f"URL:        {WHO_BASE}/{don_id}")
    print(f"PUBLISHED:  {item.get('PublicationDate', '')}")
    print(f"EVENT TYPE: {event_type}")
    print(f"BODY:       {body_preview}...")
    print(f"DB:         {status}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def main(dry_run: bool = False) -> None:
    db_pool = None
    if not dry_run:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        print("[DB] Connected to PostgreSQL")
        source_id = await ensure_who_source(db_pool)
        print(f"[DB] WHO source id={source_id}")
    else:
        source_id = -1
        print("[DRY RUN] No data will be written.")

    seen: set[str] = set()

    async with httpx.AsyncClient() as client:
        try:
            while True:
                seen.clear()
                ck_key = "who_don"
                skip   = await load_checkpoint(db_pool, ck_key) if db_pool else 0
                if skip:
                    print(f"[SOURCE] WHO DON (resuming at skip={skip})")
                else:
                    print("[SOURCE] WHO DON (from beginning)")

                items = await fetch_outbreaks(client, skip)
                if not items:
                    print("[SOURCE] No more items — resetting to skip=0 for next pass")
                    if db_pool:
                        await save_checkpoint(db_pool, ck_key, 0)
                    print("[LOOP] Next pass...")
                    continue

                for item in items:
                    don_id = item.get("DonId", "") or item.get("Id", "")
                    if not don_id or don_id in seen:
                        continue
                    seen.add(don_id)

                    full_text  = f"{item.get('Title', '')} {_strip_html(item.get('Overview'))} {_strip_html(item.get('Assessment'))}"
                    event_type = classify_event_type(full_text)

                    db_id = None
                    if not dry_run:
                        async with db_pool.acquire() as conn:
                            db_id = await upsert_outbreak(conn, item, source_id, event_type)
                        if db_id:
                            print(f"[DB] Inserted {db_id}")
                        else:
                            print(f"[DB] Skipped (duplicate): {item.get('DonId', '')}")

                    print_outbreak(item, event_type, db_id, dry_run)

                if not dry_run:
                    await save_checkpoint(db_pool, ck_key, skip + len(items))

                print("[LOOP] Next pass...")

        finally:
            if db_pool:
                await db_pool.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
