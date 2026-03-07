"""
News scraper for global event aggregation platform.
Uses newsdata.io API for feed discovery, Playwright for full article body.
Uploads hero images to S3.
Writes to PostgreSQL and uploads hero images to S3.
"""

import asyncio
import json
import mimetypes
import os
import re
import sys
from pathlib import PurePosixPath
from urllib.parse import urlparse

import asyncpg
import boto3
import httpx
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Error as PlaywrightError

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NEWSDATA_API_KEY = os.environ["NEWSDATA_API_KEY"]
NEWSDATA_URL     = "https://newsdata.io/api/1/latest"

AWS_REGION  = os.getenv("AWS_REGION", "ca-central-1")
S3_BUCKET   = os.getenv("S3_BUCKET", "")
S3_ENABLED   = bool(S3_BUCKET and os.getenv("AWS_ACCESS_KEY_ID"))
DATABASE_URL = os.environ["DATABASE_URL"]

CATEGORIES = ["world", "politics", "business", "environment", "top"]

# Country filter — keeps results globally relevant (domainurl not on free plan)
COUNTRIES = "ca,gb"

ARTICLES_PER_CATEGORY = 5
ARTICLE_TIMEOUT_MS    = 15_000
ARTICLE_TIMEOUT_S     = 20

# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

_EVENT_KEYWORDS: dict[str, list[str]] = {
    "geopolitics": [
        "war", "conflict", "military", "troops", "missile", "sanction", "diplomat",
        "treaty", "nato", "united nations", "invasion", "election", "president",
        "prime minister", "government", "coup", "protest", "attack", "geopolit",
    ],
    "trade_supply_chain": [
        "trade", "tariff", "supply chain", "export", "import", "wto", "logistics",
        "shipping", "port", "customs", "manufacturing", "factory", "semiconductor",
        "chip", "shortage",
    ],
    "energy_commodities": [
        "oil", "gas", "opec", "energy", "barrel", "pipeline", "crude", "lng",
        "coal", "nuclear", "renewabl", "solar", "wind power", "electricity",
        "wheat", "grain", "gold", "copper", "lithium", "commodity", "commodities",
    ],
    "financial_markets": [
        "stock", "market", "interest rate", "federal reserve", "inflation",
        "recession", "gdp", "currency", "dollar", "euro", "yen", "bond", "yield",
        "bank", "finance", "crypto", "bitcoin", "nasdaq", "s&p", "dow",
    ],
    "climate_disasters": [
        "climate", "hurricane", "earthquake", "flood", "wildfire", "drought",
        "tsunami", "tornado", "disaster", "storm", "emissions", "carbon",
        "sea level", "heatwave", "glacier",
    ],
    "policy_regulation": [
        "regulation", "legislation", "law", "policy", "bill", "congress", "senate",
        "parliament", "court", "ruling", "ban", "tax", "subsidy", "antitrust",
        "compliance",
    ],
}


def _parse_dt(value: str | None) -> datetime | None:
    """Parse newsdata.io pubDate string to datetime."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def classify_event_type(text: str) -> str:
    text_lower = text.lower()
    scores = {t: sum(kw in text_lower for kw in kws) for t, kws in _EVENT_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "geopolitics"
LOOP_SLEEP_S          = 600

# ---------------------------------------------------------------------------
# S3 client (lazy, non-blocking via executor)
# ---------------------------------------------------------------------------

def _make_s3():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _upload_bytes(image_bytes: bytes, s3_key: str, content_type: str) -> str:
    """Blocking S3 upload — runs in executor."""
    s3 = _make_s3()
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=image_bytes,
        ContentType=content_type,
    )
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


async def upload_image_to_s3(
    client: httpx.AsyncClient,
    image_url: str,
    article_id: str,
    source_id: str,
) -> str | None:
    """Download image and upload to S3. Returns S3 URL or None on failure."""
    if not S3_ENABLED:
        return None
    try:
        r = await client.get(image_url, timeout=10, follow_redirects=True)
        r.raise_for_status()
        image_bytes = r.content

        # Derive file extension from URL or content-type header
        content_type = r.headers.get("content-type", "image/jpeg").split(";")[0]
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        # mimetypes sometimes returns .jpe — normalise
        ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)

        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        filename = PurePosixPath(urlparse(image_url).path).name or f"hero{ext}"
        s3_key = f"images/{today}/{source_id}/{article_id}/{filename}"

        loop = asyncio.get_running_loop()
        s3_url = await loop.run_in_executor(
            None, _upload_bytes, image_bytes, s3_key, content_type
        )
        return s3_url

    except Exception as e:
        print(f"[WARN] S3 upload failed ({image_url}): {e}")
        return None


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
# newsdata.io feed fetch
# ---------------------------------------------------------------------------

async def fetch_feed(client: httpx.AsyncClient, category: str, page: str | None = None) -> tuple[list[dict], str | None]:
    params = {
        "apikey":   NEWSDATA_API_KEY,
        "language": "en",
        "category": category,
        "country":  COUNTRIES,
        "size":     ARTICLES_PER_CATEGORY,
    }
    if page:
        params["page"] = page
    try:
        r = await client.get(NEWSDATA_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("results", []), data.get("nextPage")
    except Exception as e:
        print(f"[ERROR] newsdata.io ({category}): {e}")
        return [], None


# ---------------------------------------------------------------------------
# Playwright full-body fetch
# ---------------------------------------------------------------------------

async def fetch_article_body(browser, url: str) -> dict:
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = await context.new_page()
    try:
        await page.goto(url, timeout=ARTICLE_TIMEOUT_MS, wait_until="domcontentloaded")

        body_text = ""
        for selector in [
            "article",
            '[class*="article-body"]',
            '[class*="story-body"]',
            '[class*="article__body"]',
            '[class*="content-body"]',
            "main",
        ]:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    body_text = await el.inner_text(timeout=5000)
                    body_text = re.sub(r"\s+", " ", body_text).strip()
                    if len(body_text) > 100:
                        break
            except Exception:
                continue

        return {"body": body_text}
    finally:
        await context.close()


# ---------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------

async def upsert_source(conn, source: dict) -> int:
    """Insert source if not exists, return its id."""
    row = await conn.fetchrow(
        """
        INSERT INTO sources (name, type, base_url, trust_score)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (name) DO UPDATE
            SET base_url    = EXCLUDED.base_url,
                trust_score = EXCLUDED.trust_score
        RETURNING id
        """,
        source["name"],
        source["type"],
        source["base_url"],
        source["trust_score"],
    )
    return row["id"]


async def upsert_content(conn, content: dict, source_id: int) -> str | None:
    """Insert content row, skip if URL already exists. Returns UUID or None."""
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO content_table
                (source_id, title, body, url, published_at, image_url, event_type)
            VALUES ($1, $2, $3, $4, $5::timestamptz, $6, $7)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            source_id,
            content["title"],
            content["body"],
            content["url"],
            _parse_dt(content["published_at"]),
            content["image_url"],
            content["event_type"],
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[ERROR] DB insert failed ({content['url']}): {e}")
        return None


# ---------------------------------------------------------------------------
# Print structured record
# ---------------------------------------------------------------------------

def print_record(record: dict) -> None:
    print("=" * 60)
    # Human-readable summary
    print(f"SOURCE:      {record['source']['name']}  ({record['source']['base_url']})")
    print(f"TRUST:       {record['source']['trust_score']}")
    print(f"TITLE:       {record['content']['title']}")
    print(f"URL:         {record['content']['url']}")
    print(f"PUBLISHED:   {record['content']['published_at']}")
    print(f"EVENT TYPE:  {record['content']['event_type']}")
    print(f"IMAGE (S3):  {record['content']['image_url'] or '(S3 disabled — original below)'}")
    if not record['content']['image_url']:
        print(f"IMAGE (src): {record['_original_image_url']}")
    print(f"BODY:        {(record['content']['body'] or '')[:300]}...")
    # Full structured dict for DB wiring later
    print("RECORD JSON:")
    printable = {k: v for k, v in record.items() if not k.startswith("_")}
    print(json.dumps(printable, indent=2, default=str))
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def main() -> None:
    if S3_ENABLED:
        print(f"[S3] Enabled — bucket: {S3_BUCKET} ({AWS_REGION})")
    else:
        print("[S3] Disabled — set S3_BUCKET in .env to enable image uploads")

    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    print("[DB] Connected to PostgreSQL")

    seen: set[str] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        async with httpx.AsyncClient() as client:
            try:
                while True:
                    seen.clear()

                    for category in CATEGORIES:
                        ck_key = f"newsdata_{category}"
                        page   = await load_checkpoint(db_pool, ck_key)
                        if page:
                            print(f"[SOURCE] Fetching category: {category} (resuming from checkpoint)")
                        else:
                            print(f"[SOURCE] Fetching category: {category}")

                        items, next_page = await fetch_feed(client, category, page)

                        if next_page:
                            await save_checkpoint(db_pool, ck_key, next_page)

                        for item in items:
                            url        = item.get("link", "")
                            article_id = item.get("article_id", "")
                            if not url or article_id in seen:
                                continue
                            seen.add(article_id)

                            # --- Playwright body ---
                            try:
                                article = await asyncio.wait_for(
                                    fetch_article_body(browser, url),
                                    timeout=ARTICLE_TIMEOUT_S,
                                )
                                body = article["body"]
                            except (asyncio.TimeoutError, PlaywrightError) as e:
                                if "timeout" in str(e).lower() or isinstance(e, asyncio.TimeoutError):
                                    print(f"[SKIP] Timeout: {url}")
                                else:
                                    print(f"[ERROR] Playwright: {e}")
                                body = ""
                            except Exception as e:
                                print(f"[ERROR] {item.get('source_name')}: {e}")
                                body = ""

                            # --- S3 image upload ---
                            original_image_url = item.get("image_url") or ""
                            s3_image_url = None
                            if original_image_url:
                                s3_image_url = await upload_image_to_s3(
                                    client,
                                    original_image_url,
                                    article_id,
                                    item.get("source_id", "unknown"),
                                )

                            # --- Structured record ---
                            full_text  = f"{item.get('title', '')} {body or item.get('description', '')}"
                            event_type = classify_event_type(full_text)

                            # newsdata.io source_priority: lower number = higher authority.
                            # Normalise to a 0–1 trust score (cap at 100k).
                            raw_priority = item.get("source_priority") or 100_000
                            trust_score  = round(1.0 - min(raw_priority, 100_000) / 100_000, 4)

                            record = {
                                "source": {
                                    "name":        item.get("source_name", ""),
                                    "type":        "news",
                                    "base_url":    item.get("source_url", ""),
                                    "trust_score": trust_score,
                                },
                                "content": {
                                    "title":        item.get("title", ""),
                                    "body":         body or item.get("description", ""),
                                    "url":          url,
                                    "published_at": item.get("pubDate", ""),
                                    "image_url":    s3_image_url or original_image_url,
                                    "event_type":   event_type,
                                },
                                "_original_image_url": original_image_url,
                            }

                            # --- DB writes ---
                            async with db_pool.acquire() as conn:
                                source_id  = await upsert_source(conn, record["source"])
                                content_id = await upsert_content(conn, record["content"], source_id)

                            if content_id:
                                print(f"[DB] Inserted content {content_id}")
                            else:
                                print(f"[DB] Skipped (duplicate): {url}")

                            print_record(record)

                    print(f"[LOOP] Next pass...")

            finally:
                await browser.close()
                await db_pool.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())
