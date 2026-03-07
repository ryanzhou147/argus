"""
NewsAPI.ai (Event Registry) scraper for global event intelligence platform.
Full article body returned directly by API — no Playwright needed.
Uploads hero images to S3. Writes to PostgreSQL.
"""

import asyncio
import mimetypes
import os
import sys
from datetime import datetime, timezone
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

NEWSAI_API_KEY = os.environ["NEWSAI_API_KEY"]
NEWSAI_URL     = "https://eventregistry.org/api/v1/article/getArticles"

AWS_REGION  = os.getenv("AWS_REGION", "ca-central-1")
S3_BUCKET   = os.getenv("S3_BUCKET", "")
S3_ENABLED  = bool(S3_BUCKET and os.getenv("AWS_ACCESS_KEY_ID"))
DATABASE_URL = os.environ["DATABASE_URL"]

ARTICLES_PER_QUERY = 10

# Mapped to NewsAPI.ai category URIs + keyword refinement
QUERIES = [
    {
        "label":       "geopolitics",
        "categoryUri": "news/Politics",
        "keywords":    ["war", "military", "sanctions", "NATO", "invasion", "diplomacy", "geopolitics"],
    },
    {
        "label":       "trade_supply_chain",
        "categoryUri": "news/Business",
        "keywords":    ["trade", "tariff", "supply chain", "shipping", "semiconductor", "logistics"],
    },
    {
        "label":       "energy_commodities",
        "categoryUri": "news/Business",
        "keywords":    ["oil", "gas", "OPEC", "energy", "pipeline", "LNG", "commodities"],
    },
    {
        "label":       "financial_markets",
        "categoryUri": "news/Business",
        "keywords":    ["inflation", "interest rate", "recession", "Federal Reserve", "GDP", "stock market"],
    },
    {
        "label":       "climate_disasters",
        "categoryUri": "news/Environment",
        "keywords":    ["climate", "flood", "wildfire", "hurricane", "earthquake", "emissions", "disaster"],
    },
    {
        "label":       "policy_regulation",
        "categoryUri": "news/Politics",
        "keywords":    ["regulation", "legislation", "parliament", "policy", "court ruling", "ban"],
    },
]

# Source location URIs for Canada and UK
SOURCE_LOCATIONS = [
    "http://en.wikipedia.org/wiki/Canada",
    "http://en.wikipedia.org/wiki/United_Kingdom",
]

# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

_EVENT_KEYWORDS: dict[str, list[str]] = {
    "geopolitics": [
        "war", "conflict", "military", "troops", "missile", "sanction", "diplomat",
        "treaty", "nato", "united nations", "invasion", "election", "president",
        "prime minister", "government", "coup", "protest", "attack",
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


def classify_event_type(text: str, hint: str) -> str:
    text_lower = text.lower()
    scores = {t: sum(kw in text_lower for kw in kws) for t, kws in _EVENT_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
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


async def upload_image_to_s3(client: httpx.AsyncClient, image_url: str, article_uri: str, source_id: str) -> str | None:
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
        safe_uri = article_uri.replace("/", "_").replace(":", "")[:60]
        s3_key = f"images/{today}/{source_id}/{safe_uri}/{filename}"
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_bytes, r.content, s3_key, content_type)
    except Exception as e:
        print(f"[WARN] S3 upload failed ({image_url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

async def load_checkpoint(pool, key: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT checkpoint FROM scraper_checkpoints WHERE scraper = $1", key)
        return int(row["checkpoint"]) if row else 1


async def save_checkpoint(pool, key: str, page: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO scraper_checkpoints (scraper, checkpoint, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (scraper) DO UPDATE SET checkpoint = EXCLUDED.checkpoint, updated_at = NOW()
        """, key, str(page))


# ---------------------------------------------------------------------------
# NewsAPI.ai fetch
# ---------------------------------------------------------------------------

async def fetch_articles(client: httpx.AsyncClient, query: dict, page: int = 1) -> list[dict]:
    keyword = " OR ".join(query["keywords"])
    try:
        r = await client.post(
            NEWSAI_URL,
            json={
                "apiKey":                   NEWSAI_API_KEY,
                "keyword":                  keyword,
                "keywordSearchMode":        "simple",
                "categoryUri":              query["categoryUri"],
                "lang":                     "eng",
                "sourceLocationUri":        SOURCE_LOCATIONS,
                "articlesCount":            ARTICLES_PER_QUERY,
                "articlesPage":             page,
                "articlesSortBy":           "date",
                "articlesSortByAsc":        False,
                "includeArticleBody":       True,
                "includeArticleImage":      True,
                "includeSourceTitle":       True,
                "includeSourceLocationUri": True,
                "isDuplicateFilter":        "skipDuplicates",
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("articles", {}).get("results", [])
    except Exception as e:
        print(f"[ERROR] NewsAPI.ai ({query['label']}): {e}")
        return []


# ---------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------

async def upsert_source(conn, article: dict) -> int:
    source      = article.get("source", {})
    name        = source.get("title", "unknown")
    base_url    = article.get("url", "")
    # Strip to domain only
    parsed      = urlparse(base_url)
    base_url    = f"{parsed.scheme}://{parsed.netloc}"

    row = await conn.fetchrow(
        """
        INSERT INTO sources (name, type, base_url)
        VALUES ($1, $2, $3)
        ON CONFLICT (name) DO UPDATE SET base_url = EXCLUDED.base_url
        RETURNING id
        """,
        name, "news", base_url,
    )
    return row["id"]


async def upsert_content(conn, article: dict, source_id: int, event_type: str, image_url: str) -> str | None:
    url          = article.get("url", "")
    title        = article.get("title", "")
    body         = article.get("body", "") or ""
    published_at = article.get("dateTimePub") or article.get("dateTime") or article.get("date")

    # Parse datetime
    dt = None
    if published_at:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(published_at, fmt).replace(tzinfo=timezone.utc)
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
            source_id, title, body, url, dt, image_url or None, event_type,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[ERROR] DB insert failed ({url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

def print_article(article: dict, event_type: str, image_url: str, db_id: str | None, dry_run: bool) -> None:
    status = "dry run" if dry_run else (f"inserted {db_id}" if db_id else "duplicate")
    body_preview = (article.get("body") or "")[:300].replace("\n", " ")
    print("=" * 60)
    print(f"SOURCE:     {article.get('source', {}).get('title', '?')}")
    print(f"TITLE:      {article.get('title', '')}")
    print(f"URL:        {article.get('url', '')}")
    print(f"PUBLISHED:  {article.get('dateTimePub') or article.get('date', '')}")
    print(f"EVENT TYPE: {event_type}")
    print(f"IMAGE:      {image_url or '(none)'}")
    print(f"BODY:       {body_preview}...")
    print(f"DB:         {status}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def main(dry_run: bool = False) -> None:
    if S3_ENABLED:
        print(f"[S3] Enabled — bucket: {S3_BUCKET}")
    else:
        print("[S3] Disabled — set S3_BUCKET in .env to enable")

    db_pool = None
    if not dry_run:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        print("[DB] Connected to PostgreSQL")
    else:
        print("[DRY RUN] No data will be written.")

    seen: set[str] = set()

    async with httpx.AsyncClient() as client:
        try:
            while True:
                seen.clear()

                for query in QUERIES:
                    ck_key = f"newsai_{query['label']}"
                    page   = await load_checkpoint(db_pool, ck_key) if db_pool else 1
                    if page > 1:
                        print(f"[SOURCE] Fetching: {query['label']} (resuming page {page})")
                    else:
                        print(f"[SOURCE] Fetching: {query['label']}")
                    articles = await fetch_articles(client, query, page)

                    for article in articles:
                        url = article.get("url", "")
                        uri = article.get("uri", url)

                        if not url or uri in seen:
                            continue
                        seen.add(uri)

                        full_text  = f"{article.get('title', '')} {article.get('body', '')}"
                        event_type = classify_event_type(full_text, query["label"])

                        # S3 image upload
                        raw_image = article.get("image", "") or ""
                        image_url = raw_image
                        if raw_image and not dry_run:
                            source_id_str = article.get("source", {}).get("uri", "unknown").replace("/", "_")
                            uploaded = await upload_image_to_s3(client, raw_image, uri, source_id_str)
                            if uploaded:
                                image_url = uploaded

                        db_id = None
                        if not dry_run:
                            async with db_pool.acquire() as conn:
                                source_id = await upsert_source(conn, article)
                                db_id     = await upsert_content(conn, article, source_id, event_type, image_url)
                            if db_id:
                                print(f"[DB] Inserted {db_id}")
                            else:
                                print(f"[DB] Skipped (duplicate): {url}")

                        print_article(article, event_type, image_url, db_id, dry_run)

                    if not dry_run and articles:
                        await save_checkpoint(db_pool, ck_key, page + 1)

                print("[LOOP] Next pass...")

        finally:
            if db_pool:
                await db_pool.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
