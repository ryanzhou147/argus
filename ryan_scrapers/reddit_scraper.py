"""
Reddit scraper for global event intelligence platform.
Scrapes post titles and bodies from high-signal subreddits.
Filters to posts within the last two weeks.
Writes to PostgreSQL (same content_table + sources as news scraper).
No Playwright needed — Reddit JSON API returns full text.
"""

import asyncio
import mimetypes
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import PurePosixPath
from urllib.parse import urlparse

import asyncpg
import boto3
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL   = os.environ["DATABASE_URL"]
AWS_REGION     = os.getenv("AWS_REGION", "ca-central-1")
S3_BUCKET      = os.getenv("S3_BUCKET", "")
S3_ENABLED     = bool(S3_BUCKET and os.getenv("AWS_ACCESS_KEY_ID"))
TWO_WEEKS_AGO  = lambda: datetime.now(timezone.utc) - timedelta(weeks=2)
POSTS_PER_SUB  = 25
REQUEST_DELAY  = 5

REDDIT_HEADERS = {
    "User-Agent": "hackcanada-event-scraper/1.0 (research project)",
}

# ---------------------------------------------------------------------------
# Subreddits
# ---------------------------------------------------------------------------

SUBREDDITS = [
    # Top tier signal
    {"name": "geopolitics",       "tier": 1, "event_type_hint": "geopolitics"},
    {"name": "CredibleDefense",   "tier": 1, "event_type_hint": "geopolitics"},
    {"name": "WarCollege",        "tier": 1, "event_type_hint": "geopolitics"},
    {"name": "Commodities",       "tier": 1, "event_type_hint": "energy_commodities"},
    {"name": "supplychain",       "tier": 1, "event_type_hint": "trade_supply_chain"},
    # Second tier signal
    {"name": "EnergyTrading",     "tier": 2, "event_type_hint": "energy_commodities"},
    {"name": "PoliticalEconomy",  "tier": 2, "event_type_hint": "policy_regulation"},
    {"name": "SecurityAnalysis",  "tier": 2, "event_type_hint": "financial_markets"},
    {"name": "oil",               "tier": 2, "event_type_hint": "energy_commodities"},
    {"name": "logistics",         "tier": 2, "event_type_hint": "trade_supply_chain"},
    # Third tier / hidden gems
    {"name": "IRstudies",           "tier": 3, "event_type_hint": "geopolitics"},
    {"name": "climate",             "tier": 3, "event_type_hint": "climate_disasters"},
    {"name": "collapse",            "tier": 3, "event_type_hint": "climate_disasters"},
    {"name": "lesscredibledefense", "tier": 3, "event_type_hint": "geopolitics"},
    {"name": "energy",              "tier": 3, "event_type_hint": "energy_commodities"},
    {"name": "ChinaEconomy",        "tier": 3, "event_type_hint": "financial_markets"},
    {"name": "econmonitor",         "tier": 3, "event_type_hint": "financial_markets"},
    {"name": "globalpowers",        "tier": 3, "event_type_hint": "geopolitics"},
    # New additions — geopolitics
    {"name": "MiddleEast",          "tier": 2, "event_type_hint": "geopolitics"},
    {"name": "ukraine",             "tier": 2, "event_type_hint": "geopolitics"},
    {"name": "china",               "tier": 2, "event_type_hint": "geopolitics"},
    {"name": "NeutralPolitics",     "tier": 2, "event_type_hint": "policy_regulation"},
    {"name": "IndoPacific",         "tier": 3, "event_type_hint": "geopolitics"},
    # New additions — economics/finance
    {"name": "economics",           "tier": 2, "event_type_hint": "financial_markets"},
    {"name": "MacroEconomics",      "tier": 2, "event_type_hint": "financial_markets"},
    {"name": "investing",           "tier": 2, "event_type_hint": "financial_markets"},
    {"name": "CanadaEconomy",       "tier": 2, "event_type_hint": "financial_markets"},
    # New additions — energy
    {"name": "RenewableEnergy",     "tier": 3, "event_type_hint": "energy_commodities"},
    {"name": "nuclear",             "tier": 3, "event_type_hint": "energy_commodities"},
    {"name": "petroleum",           "tier": 3, "event_type_hint": "energy_commodities"},
    # New additions — Canada
    {"name": "CanadaPolitics",      "tier": 2, "event_type_hint": "policy_regulation"},
    {"name": "canadabusiness",      "tier": 3, "event_type_hint": "trade_supply_chain"},
    # New additions — climate
    {"name": "environment",         "tier": 3, "event_type_hint": "climate_disasters"},
    {"name": "ClimateChange",       "tier": 3, "event_type_hint": "climate_disasters"},
]

# Trust score by tier
TIER_TRUST = {1: 0.85, 2: 0.65, 3: 0.45}

# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

_EVENT_KEYWORDS: dict[str, list[str]] = {
    "geopolitics": [
        "war", "conflict", "military", "troops", "missile", "sanction", "diplomat",
        "treaty", "nato", "united nations", "invasion", "election", "president",
        "prime minister", "government", "coup", "protest", "attack", "geopolit",
        "defense", "defence", "intelligence", "alliance", "sovereignty",
    ],
    "trade_supply_chain": [
        "trade", "tariff", "supply chain", "export", "import", "wto", "logistics",
        "shipping", "port", "customs", "manufacturing", "factory", "semiconductor",
        "chip", "shortage", "container", "freight", "procurement",
    ],
    "energy_commodities": [
        "oil", "gas", "opec", "energy", "barrel", "pipeline", "crude", "lng",
        "coal", "nuclear", "renewabl", "solar", "wind power", "electricity",
        "wheat", "grain", "gold", "copper", "lithium", "commodity", "commodities",
        "refin", "drilling", "upstream", "downstream",
    ],
    "financial_markets": [
        "stock", "market", "interest rate", "federal reserve", "inflation",
        "recession", "gdp", "currency", "dollar", "euro", "yen", "bond", "yield",
        "bank", "finance", "crypto", "bitcoin", "nasdaq", "s&p", "dow",
        "equity", "hedge", "macro", "monetary policy",
    ],
    "climate_disasters": [
        "climate", "hurricane", "earthquake", "flood", "wildfire", "drought",
        "tsunami", "tornado", "disaster", "storm", "emissions", "carbon",
        "sea level", "heatwave", "glacier", "net zero", "decarbon",
    ],
    "policy_regulation": [
        "regulation", "legislation", "law", "policy", "bill", "congress", "senate",
        "parliament", "court", "ruling", "ban", "tax", "subsidy", "antitrust",
        "compliance", "industrial policy", "sanctions regime",
    ],
}


def classify_event_type(text: str, hint: str) -> str:
    text_lower = text.lower()
    scores = {t: sum(kw in text_lower for kw in kws) for t, kws in _EVENT_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    # Fall back to subreddit hint if no keywords match
    return best if scores[best] > 0 else hint


# ---------------------------------------------------------------------------
# S3 upload
# ---------------------------------------------------------------------------

def _upload_bytes(image_bytes: bytes, s3_key: str, content_type: str) -> str:
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=image_bytes, ContentType=content_type)
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


async def upload_image_to_s3(client: httpx.AsyncClient, image_url: str, post_id: str, subreddit: str) -> str | None:
    if not S3_ENABLED:
        return None
    try:
        r = await client.get(image_url, timeout=10, follow_redirects=True)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "image/jpeg").split(";")[0]
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)
        today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        filename = PurePosixPath(urlparse(image_url).path).name or f"hero{ext}"
        s3_key = f"images/{today}/reddit_{subreddit.lower()}/{post_id}/{filename}"
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_bytes, r.content, s3_key, content_type)
    except Exception as e:
        print(f"[WARN] S3 upload failed ({image_url}): {e}")
        return None


def extract_image_url(post: dict) -> str:
    """Extract best available image URL from a Reddit post."""
    # 1. High-res preview image (most reliable)
    try:
        preview_url = post["preview"]["images"][0]["source"]["url"]
        # Reddit escapes ampersands in preview URLs
        return preview_url.replace("&amp;", "&")
    except (KeyError, IndexError):
        pass

    # 2. Direct image link
    url = post.get("url", "")
    if any(url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return url

    # 3. Thumbnail (last resort — often low quality)
    thumb = post.get("thumbnail", "")
    if thumb and thumb.startswith("http"):
        return thumb

    return ""


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

async def load_checkpoint(pool, key: str) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT checkpoint FROM scraper_checkpoints WHERE scraper = $1", key)
        return row["checkpoint"] if row else None


async def save_checkpoint(pool, key: str, value: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO scraper_checkpoints (scraper, checkpoint, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (scraper) DO UPDATE SET checkpoint = EXCLUDED.checkpoint, updated_at = NOW()
        """, key, value)


# ---------------------------------------------------------------------------
# Reddit fetch
# ---------------------------------------------------------------------------

async def fetch_subreddit(client: httpx.AsyncClient, subreddit: str, after: str | None = None) -> tuple[list[dict], str | None]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json"
    params = {"limit": POSTS_PER_SUB}
    if after:
        params["after"] = after
    for attempt in range(3):
        try:
            r = await client.get(url, params=params, timeout=15)
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"[RATE LIMIT] r/{subreddit} — waiting {wait}s")
                await asyncio.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()["data"]
            posts = [child["data"] for child in data["children"]]
            return posts, data.get("after")
        except Exception as e:
            print(f"[ERROR] r/{subreddit}: {e}")
            return [], None
    print(f"[SKIP] r/{subreddit}: gave up after 3 attempts")
    return [], None


# ---------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------

async def upsert_source(conn, name: str, base_url: str, trust_score: float) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO sources (name, type, base_url, trust_score)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (name) DO UPDATE
            SET base_url    = EXCLUDED.base_url,
                trust_score = EXCLUDED.trust_score
        RETURNING id
        """,
        name, "reddit", base_url, trust_score,
    )
    return row["id"]


async def upsert_content(conn, source_id: int, post: dict, event_type: str, image_url: str) -> str | None:
    url        = f"https://reddit.com{post['permalink']}"
    title      = post.get("title", "")
    body       = post.get("selftext", "") or ""
    published  = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)

    if body in ("[deleted]", "[removed]"):
        body = ""

    try:
        row = await conn.fetchrow(
            """
            INSERT INTO content_table
                (source_id, title, body, url, published_at, event_type, image_url)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            source_id, title, body, url, published, event_type, image_url or None,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[ERROR] DB insert failed ({url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

def print_post(subreddit: str, post: dict, event_type: str, image_url: str, db_id: str | None, dry_run: bool = False) -> None:
    body_preview = (post.get("selftext") or "")[:200].replace("\n", " ")
    status = "dry run" if dry_run else (f"inserted {db_id}" if db_id else "duplicate")
    print("=" * 60)
    print(f"SUBREDDIT:  r/{subreddit}")
    print(f"TITLE:      {post.get('title', '')}")
    print(f"AUTHOR:     u/{post.get('author', '')}")
    print(f"SCORE:      {post.get('score', 0)}  |  COMMENTS: {post.get('num_comments', 0)}")
    print(f"PUBLISHED:  {datetime.fromtimestamp(post['created_utc'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"EVENT TYPE: {event_type}")
    print(f"IMAGE:      {image_url or '(none)'}")
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

    cutoff = TWO_WEEKS_AGO()
    print(f"[FILTER] Only posts after {cutoff.strftime('%Y-%m-%d')}")

    async with httpx.AsyncClient(headers=REDDIT_HEADERS) as client:
        try:
            while True:
                cutoff = TWO_WEEKS_AGO()  # refresh each pass

                for sub in SUBREDDITS:
                    name  = sub["name"]
                    tier  = sub["tier"]
                    hint  = sub["event_type_hint"]
                    trust = TIER_TRUST[tier]

                    ck_key = f"reddit_{name.lower()}"
                    after  = await load_checkpoint(db_pool, ck_key) if db_pool else None
                    if after:
                        print(f"[SOURCE] r/{name} (tier {tier}, resuming from checkpoint)")
                    else:
                        print(f"[SOURCE] r/{name} (tier {tier})")
                    posts, next_after = await fetch_subreddit(client, name, after)

                    source_id = None
                    if not dry_run:
                        async with db_pool.acquire() as conn:
                            source_id = await upsert_source(
                                conn,
                                name=f"reddit_r_{name.lower()}",
                                base_url=f"https://reddit.com/r/{name}",
                                trust_score=trust,
                            )

                    new_count = 0
                    for post in posts:
                        # Two-week cutoff filter
                        created = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)
                        if created < cutoff:
                            continue

                        # Skip posts with no title or no body
                        body_text = post.get("selftext", "") or ""
                        if not post.get("title") or body_text in ("", "[deleted]", "[removed]"):
                            continue

                        event_type = classify_event_type(
                            f"{post.get('title', '')} {post.get('selftext', '')}",
                            hint,
                        )

                        # --- Image ---
                        raw_image_url = extract_image_url(post)
                        image_url = raw_image_url
                        if raw_image_url and not dry_run:
                            uploaded = await upload_image_to_s3(client, raw_image_url, post["id"], name)
                            if uploaded:
                                image_url = uploaded

                        db_id = None
                        if not dry_run:
                            async with db_pool.acquire() as conn:
                                db_id = await upsert_content(conn, source_id, post, event_type, image_url)
                            if db_id:
                                new_count += 1

                        print_post(name, post, event_type, image_url, db_id, dry_run)

                    if next_after and db_pool:
                        await save_checkpoint(db_pool, ck_key, next_after)
                    print(f"[r/{name}] {new_count} new posts written")
                    await asyncio.sleep(REQUEST_DELAY)

                print("[LOOP] Next pass...")

        finally:
            if db_pool:
                await db_pool.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[DRY RUN] No data will be written to the database.")
    asyncio.run(main(dry_run=dry_run))
