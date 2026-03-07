"""
Hacker News scraper for global event intelligence platform.
Uses the official Firebase HN API — no Playwright needed.
Pulls top, best, and new stories. Filters by score >= 50.
Writes to PostgreSQL: sources, engagement, content_table.
"""

import asyncio
import html
import os
import sys
from datetime import datetime, timezone

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HN_BASE      = "https://hacker-news.firebaseio.com/v0"
HN_ITEM_URL  = f"{HN_BASE}/item/{{id}}.json"
HN_LISTS     = {
    "topstories": f"{HN_BASE}/topstories.json",
    "beststories": f"{HN_BASE}/beststories.json",
    "newstories":  f"{HN_BASE}/newstories.json",
}

DATABASE_URL  = os.environ["DATABASE_URL"]
MIN_SCORE     = 50       # ignore low-signal posts
MAX_PER_LIST  = 200      # top N IDs to consider per list endpoint
CONCURRENCY   = 10       # parallel item fetches

# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

_EVENT_KEYWORDS: dict[str, list[str]] = {
    "geopolitics": [
        "war", "conflict", "military", "sanction", "nato", "invasion", "election",
        "government", "coup", "protest", "attack", "ukraine", "russia", "china",
        "taiwan", "missile", "nuclear weapon", "diplomat",
    ],
    "trade_supply_chain": [
        "trade", "tariff", "supply chain", "export", "import", "wto", "logistics",
        "shipping", "port", "customs", "manufacturing", "semiconductor", "chip",
        "shortage", "factory",
    ],
    "energy_commodities": [
        "oil", "gas", "opec", "energy", "pipeline", "crude", "lng", "coal",
        "nuclear", "solar", "wind power", "electricity", "wheat", "grain",
        "gold", "copper", "lithium", "commodity",
    ],
    "financial_markets": [
        "stock", "market", "interest rate", "federal reserve", "inflation",
        "recession", "gdp", "currency", "dollar", "euro", "bond", "yield",
        "bank", "finance", "crypto", "bitcoin", "nasdaq", "s&p", "dow",
        "ipo", "startup", "funding", "venture",
    ],
    "climate_disasters": [
        "climate", "hurricane", "earthquake", "flood", "wildfire", "drought",
        "tsunami", "tornado", "disaster", "storm", "emissions", "carbon",
        "sea level", "heatwave", "glacier", "renewable",
    ],
    "policy_regulation": [
        "regulation", "legislation", "law", "policy", "bill", "congress", "senate",
        "parliament", "court", "ruling", "ban", "tax", "antitrust", "compliance",
        "gdpr", "ai act", "sec", "ftc", "fda", "fcc",
    ],
}


def classify_event_type(text: str) -> str:
    text_lower = text.lower()
    scores = {t: sum(kw in text_lower for kw in kws) for t, kws in _EVENT_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "policy_regulation"


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

async def load_seen_ids(pool) -> set[int]:
    """Load all HN item IDs already in content_table to avoid re-fetching."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT url FROM content_table WHERE url LIKE '%news.ycombinator.com/item%'"
        )
    ids = set()
    for row in rows:
        try:
            ids.add(int(row["url"].split("id=")[-1]))
        except (ValueError, IndexError):
            pass
    return ids


# ---------------------------------------------------------------------------
# HN API fetch
# ---------------------------------------------------------------------------

async def fetch_story_ids(client: httpx.AsyncClient, list_name: str) -> list[int]:
    try:
        r = await client.get(HN_LISTS[list_name], timeout=15)
        r.raise_for_status()
        ids = r.json()
        return ids[:MAX_PER_LIST] if isinstance(ids, list) else []
    except Exception as e:
        print(f"[ERROR] HN list {list_name}: {e}")
        return []


async def fetch_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    try:
        r = await client.get(HN_ITEM_URL.format(id=item_id), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERROR] HN item {item_id}: {e}")
        return None


async def fetch_items_concurrent(client: httpx.AsyncClient, ids: list[int]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded_fetch(item_id: int) -> dict | None:
        async with sem:
            return await fetch_item(client, item_id)

    results = await asyncio.gather(*[bounded_fetch(i) for i in ids])
    return [r for r in results if r and r.get("type") == "story" and not r.get("deleted") and not r.get("dead")]


# ---------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------

HN_SOURCE = {
    "name":        "Hacker News",
    "type":        "forum",
    "base_url":    "https://news.ycombinator.com",
    "trust_score": 0.75,
}


async def ensure_hn_source(pool) -> int:
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
            HN_SOURCE["name"], HN_SOURCE["type"],
            HN_SOURCE["base_url"], HN_SOURCE["trust_score"],
        )
        return row["id"]


async def upsert_story(conn, story: dict, source_id: int) -> str | None:
    item_id     = story["id"]
    title       = html.unescape(story.get("title", ""))
    raw_text    = story.get("text", "") or ""
    body        = html.unescape(raw_text).replace("<p>", "\n").replace("</p>", "") if raw_text else None
    unix_time   = story.get("time")
    dt          = datetime.fromtimestamp(unix_time, tz=timezone.utc) if unix_time else None

    # Canonical URL: external link or HN thread
    url = story.get("url") or f"https://news.ycombinator.com/item?id={item_id}"

    full_text  = f"{title} {body or ''}"
    event_type = classify_event_type(full_text)

    try:
        # Upsert content row (no engagement — HN score/comments don't map to reddit_* columns)
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
        print(f"[ERROR] DB insert failed (hn/{item_id}): {e}")
        return None


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

def print_story(story: dict, event_type: str, db_id: str | None, dry_run: bool) -> None:
    status = "dry run" if dry_run else (f"inserted {db_id}" if db_id else "duplicate")
    title  = html.unescape(story.get("title", ""))
    url    = story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}"
    print("=" * 60)
    print(f"HN ID:      {story['id']}")
    print(f"TITLE:      {title}")
    print(f"URL:        {url}")
    print(f"SCORE:      {story.get('score', 0)}  COMMENTS: {story.get('descendants', 0)}")
    print(f"AUTHOR:     {story.get('by', '?')}")
    print(f"PUBLISHED:  {datetime.fromtimestamp(story.get('time', 0), tz=timezone.utc).isoformat()}")
    print(f"EVENT TYPE: {event_type}")
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
        source_id = await ensure_hn_source(db_pool)
        print(f"[DB] HN source id={source_id}")
    else:
        source_id = -1
        print("[DRY RUN] No data will be written.")

    async with httpx.AsyncClient() as client:
        try:
            while True:
                # Load already-seen IDs from DB to skip duplicates without a fetch
                seen: set[int] = set()
                if db_pool:
                    seen = await load_seen_ids(db_pool)
                    print(f"[INFO] {len(seen)} HN stories already in DB")

                all_ids: set[int] = set()
                for list_name in HN_LISTS:
                    ids = await fetch_story_ids(client, list_name)
                    new_ids = [i for i in ids if i not in seen]
                    print(f"[SOURCE] {list_name}: {len(ids)} ids, {len(new_ids)} new")
                    all_ids.update(new_ids)

                print(f"[INFO] Fetching {len(all_ids)} items...")
                stories = await fetch_items_concurrent(client, list(all_ids))

                # Filter by minimum score
                stories = [s for s in stories if s.get("score", 0) >= MIN_SCORE]
                print(f"[INFO] {len(stories)} stories pass score >= {MIN_SCORE}")

                # Keep only stories with self-text (Ask HN, Show HN, text posts)
                stories = [s for s in stories if s.get("text")]
                print(f"[INFO] {len(stories)} stories have body text")

                inserted = 0
                for story in sorted(stories, key=lambda s: s.get("score", 0), reverse=True):
                    full_text  = f"{story.get('title', '')} {story.get('text', '') or ''}"
                    event_type = classify_event_type(full_text)

                    db_id = None
                    if not dry_run:
                        async with db_pool.acquire() as conn:
                            db_id = await upsert_story(conn, story, source_id)
                        if db_id:
                            inserted += 1
                            print(f"[DB] Inserted {db_id}")
                        else:
                            print(f"[DB] Skipped (duplicate): hn/{story['id']}")

                    print_story(story, event_type, db_id, dry_run)

                print(f"[LOOP] Pass complete — {inserted} inserted. Next pass...")

        finally:
            if db_pool:
                await db_pool.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
