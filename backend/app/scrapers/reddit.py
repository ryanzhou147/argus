import time
import uuid
from datetime import datetime, timezone, timedelta

import requests
import trafilatura

from . import reddit_classifier as classifier
from . import reddit_db as db

SUBREDDITS = [
    "worldnews", "geopolitics", "Economics", "investing",
    "energy", "environment", "climate", "naturaldisasters", "politics",
]

CUTOFF_DAYS = 14
MAX_POSTS = 500      # per subreddit
BATCH_SIZE = 100     # max Reddit allows per request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")

# Domains where article text extraction doesn't apply
SKIP_DOMAINS = (
    "reddit.com", "redd.it", "i.redd.it", "v.redd.it",
    "youtube.com", "youtu.be",
    "twitter.com", "x.com",
    "instagram.com", "tiktok.com",
)


def clean_body(text: str) -> str | None:
    if not text or text.strip() in ("[removed]", "[deleted]"):
        return None
    return text.strip()


def extract_image_url(p: dict) -> str | None:
    """Extract an image URL from a Reddit post's API data if one exists."""
    if p.get("post_hint") == "image":
        url = p.get("url", "")
        if url and url.lower().endswith(IMAGE_EXTENSIONS):
            return url

    preview = p.get("preview", {})
    images = preview.get("images", [])
    if images:
        source = images[0].get("source", {})
        url = source.get("url", "")
        if url:
            return url.replace("&amp;", "&")

    return None


def fetch_article_text(url: str) -> str | None:
    """Fetch and extract main article text from an external URL."""
    if not url:
        return None

    lower = url.lower()
    if any(domain in lower for domain in SKIP_DOMAINS):
        return None
    if lower.endswith(IMAGE_EXTENSIONS):
        return None

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
    except Exception:
        pass

    return None


def fetch_subreddit_posts(subreddit: str, cutoff: datetime) -> list[dict]:
    posts = []
    after = None

    while len(posts) < MAX_POSTS:
        params = {"t": "month", "limit": BATCH_SIZE}
        if after:
            params["after"] = after

        url = f"https://www.reddit.com/r/{subreddit}/top.json"

        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        except requests.RequestException as e:
            print(f"  [WARN] Network error: {e}")
            break

        if resp.status_code == 429:
            print("  [WARN] Rate limited — sleeping 60s")
            time.sleep(60)
            continue

        if resp.status_code != 200:
            print(f"  [WARN] HTTP {resp.status_code} — skipping subreddit")
            break

        data = resp.json()["data"]
        children = data["children"]

        if not children:
            break

        for child in children:
            p = child["data"]
            published_at = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc)
            if published_at < cutoff:
                continue

            is_self = p.get("is_self", False)
            external_url = None if is_self else p.get("url")

            posts.append({
                "title":        p["title"],
                "body":         clean_body(p.get("selftext", "")),
                "image_url":    extract_image_url(p),
                "external_url": external_url,
                "permalink":    p["permalink"],
                "score":        p["score"],
                "num_comments": p["num_comments"],
                "published_at": published_at,
            })

        after = data.get("after")
        if not after:
            break

        time.sleep(1)

    return posts


def main():
    conn = db.get_connection()
    source_id = db.get_or_create_source(
        conn,
        name="reddit",
        type_="social",
        base_url="https://www.reddit.com",
        trust_score=0.6,
    )

    cursor = conn.cursor()
    cutoff = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)

    total_inserted = 0
    total_skipped = 0
    total_articles = 0

    for subreddit in SUBREDDITS:
        print(f"[{subreddit}] Fetching...")
        posts = fetch_subreddit_posts(subreddit, cutoff)
        print(f"[{subreddit}] {len(posts)} posts — fetching article text...")

        for p in posts:
            body = p["body"]

            # For link posts, attempt to pull article text from the external URL
            if body is None and p["external_url"]:
                body = fetch_article_text(p["external_url"])
                if body:
                    total_articles += 1
                time.sleep(0.5)  # be polite to external sites

            post = {
                "id":            uuid.uuid4(),
                "source_id":     source_id,
                "event_type":    classifier.classify(p["title"], subreddit),
                "engagement_id": uuid.uuid4(),
                "title":         p["title"],
                "body":          body,
                "image_url":     p["image_url"],
                "url":           "https://reddit.com" + p["permalink"],
                "published_at":  p["published_at"],
                "upvotes":       p["score"],
                "comments":      p["num_comments"],
            }

            try:
                inserted = db.upsert_post(cursor, post)
                conn.commit()
                total_inserted += inserted
                total_skipped += not inserted
            except Exception as e:
                conn.rollback()
                print(f"  [ERROR] {p['title'][:60]}: {e}")

        time.sleep(2)

    cursor.close()
    conn.close()
    print(f"\nDone — inserted: {total_inserted}, duplicates skipped: {total_skipped}, articles fetched: {total_articles}")


if __name__ == "__main__":
    main()
