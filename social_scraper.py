#!/usr/bin/env python3
"""
Social media video scraper for global event intelligence.

Scrapes X (Twitter) via Playwright, downloads media to S3, writes to PostgreSQL.
No AI enrichment — pure data only.

Usage:
    uv run social_scraper.py --platform x --limit 2
    uv run social_scraper.py --platform x --limit 10
    uv run social_scraper.py --platform all --limit 10

Required env vars (.env):
    DATABASE_URL
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION / S3_BUCKET
    X_USERNAME / X_PASSWORD

Optional:
    IG_USERNAME / IG_PASSWORD
"""

import os
import sys
import json
import uuid
import asyncio
import argparse
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import quote_plus

import boto3
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import instaloader
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Response

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")
X_USERNAME   = os.getenv("X_USERNAME", "")
X_PASSWORD   = os.getenv("X_PASSWORD", "")
IG_USERNAME  = os.getenv("IG_USERNAME", "")
IG_PASSWORD  = os.getenv("IG_PASSWORD", "")
TT_USERNAME  = os.getenv("TT_USERNAME", "")
TT_PASSWORD  = os.getenv("TT_PASSWORD", "")
AWS_REGION   = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET    = os.getenv("S3_BUCKET", "hackcanada")

if not DATABASE_URL:
    sys.exit("ERROR: DATABASE_URL not set")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# ─── Search terms per event category ─────────────────────────────────────────

X_SEARCH_QUERIES: dict[str, list[str]] = {
    "geopolitics": [
        "war conflict invasion ceasefire diplomacy",
        "NATO sanctions coup geopolitics",
        "Ukraine Russia missile attack",
        "Middle East Israel Gaza war",
        "China Taiwan military tensions",
        "nuclear weapons threat deterrence",
    ],
    "trade_supply_chain": [
        "tariffs trade war supply chain disruption",
        "shipping port logistics trade deal",
        "US China trade tariffs imports exports",
        "semiconductor chip shortage supply",
        "USMCA Canada Mexico trade",
        "container shipping freight rates",
    ],
    "energy_commodities": [
        "oil price OPEC crude energy crisis",
        "natural gas LNG pipeline energy supply",
        "oil price drop surge barrel",
        "Alberta oil sands pipeline Keystone",
        "coal lithium copper commodity prices",
        "energy transition renewable solar wind",
    ],
    "financial_markets": [
        "stock market crash recession inflation",
        "interest rates central bank Fed monetary policy",
        "TSX S&P500 Nasdaq market rally selloff",
        "Bank of Canada rate decision",
        "crypto Bitcoin Ethereum market",
        "bond yield dollar currency collapse",
    ],
    "climate_disasters": [
        "hurricane earthquake wildfire flood tsunami",
        "extreme weather drought heatwave cyclone",
        "Canada wildfire BC Alberta flood",
        "tornado disaster emergency evacuation",
        "ice storm blizzard snowstorm warning",
        "landslide mudslide flooding damage",
    ],
    "policy_regulation": [
        "regulation legislation executive order new law",
        "government policy sanctions reform compliance",
        "Canada parliament bill budget policy",
        "US Congress Senate vote bill passed",
        "EU regulation policy decision",
        "immigration visa border policy reform",
    ],
}

IG_HASHTAGS: dict[str, list[str]] = {
    "geopolitics":        ["worldnews", "geopolitics", "conflict", "war"],
    "trade_supply_chain": ["tradewar", "supplychain", "tariffs", "globaltrade"],
    "energy_commodities": ["oilprice", "energy", "commodities", "opec"],
    "financial_markets":  ["stockmarket", "recession", "inflation", "finance"],
    "climate_disasters":  ["climatechange", "naturaldisaster", "wildfire", "flood"],
    "policy_regulation":  ["policy", "legislation", "government", "regulation"],
}

# ─── Text helpers ─────────────────────────────────────────────────────────────

def split_title_body(text: str) -> tuple[str, str]:
    """First sentence → title, remainder → body."""
    text = text.strip()
    for sep in (". ", "! ", "? ", "\n"):
        idx = text.find(sep)
        if idx != -1 and idx > 10:
            return text[: idx + 1].strip(), text[idx + 1 :].strip()
    # No sentence boundary found — use first 100 chars as title
    return text[:100].strip(), text[100:].strip() or None


# ─── S3 media upload ─────────────────────────────────────────────────────────

def upload_to_s3(url: str, s3_key: str, content_type: str) -> Optional[str]:
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=resp.content, ContentType=content_type)
        return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    except Exception as e:
        log.warning(f"  S3 upload failed {url[:60]}: {e}")
        return None


def upload_media(item: dict) -> dict:
    tid = item.get("tweet_id") or str(uuid.uuid4())
    platform = item["platform"]

    if item.get("video_url"):
        s3_url = upload_to_s3(item["video_url"], f"media/{platform}/{tid}.mp4", "video/mp4")
        if s3_url:
            item["video_url"] = s3_url
            log.info(f"  Video → {s3_url}")

    if item.get("image_url"):
        s3_url = upload_to_s3(item["image_url"], f"media/{platform}/{tid}_thumb.jpg", "image/jpeg")
        if s3_url:
            item["image_url"] = s3_url
            log.info(f"  Thumb → {s3_url}")

    return item


# ─── X scraper (Playwright — no API key) ─────────────────────────────────────

def _parse_tweet_result(result: dict) -> Optional[dict]:
    try:
        typename = result.get("__typename", "")
        if typename not in ("Tweet", "TweetWithVisibilityResults"):
            return None
        if typename == "TweetWithVisibilityResults":
            result = result.get("tweet", result)

        legacy = result.get("legacy", {})
        if not legacy:
            return None

        # Video-only — must have an MP4 URL
        extended    = legacy.get("extended_entities", {})
        video_media = [m for m in extended.get("media", []) if m.get("type") in ("video", "animated_gif")]
        if not video_media:
            return None

        media     = video_media[0]
        variants  = media.get("video_info", {}).get("variants", [])
        mp4s      = [v for v in variants if v.get("content_type") == "video/mp4"]
        if not mp4s:
            return None
        # Cap at ~2Mbps (720p) to avoid downloading massive 4K files
        mp4s_sorted = sorted(mp4s, key=lambda v: v.get("bitrate", 0))
        capped = [v for v in mp4s_sorted if v.get("bitrate", 0) <= 2_000_000]
        video_url = (capped[-1] if capped else mp4s_sorted[0])["url"]

        tweet_id  = legacy.get("id_str") or result.get("rest_id", "")
        text      = legacy.get("full_text", "").strip()

        try:
            published_at = datetime.strptime(
                legacy.get("created_at", ""), "%a %b %d %H:%M:%S +0000 %Y"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            published_at = datetime.now(timezone.utc)

        views = int((result.get("views") or {}).get("count", 0) or 0)

        # Geo: try exact coordinates first, fall back to place bounding box center
        lat = lon = None
        coords = legacy.get("coordinates")
        if coords and coords.get("coordinates"):
            lon, lat = coords["coordinates"]  # GeoJSON order: [lon, lat]
        else:
            place = legacy.get("place")
            if place:
                bbox = (place.get("bounding_box") or {}).get("coordinates", [])
                if bbox and bbox[0]:
                    pts = bbox[0]  # list of [lon, lat] corners
                    lon = sum(p[0] for p in pts) / len(pts)
                    lat = sum(p[1] for p in pts) / len(pts)

        return {
            "tweet_id":         tweet_id,
            "text":             text,
            "url":              f"https://x.com/i/web/status/{tweet_id}",
            "published_at":     published_at,
            "image_url":        media.get("media_url_https"),
            "video_url":        video_url,
            "latitude":         lat,
            "longitude":        lon,
            "twitter_likes":    legacy.get("favorite_count", 0),
            "twitter_views":    views,
            "twitter_comments": legacy.get("reply_count", 0),
            "twitter_reposts":  legacy.get("retweet_count", 0),
        }
    except Exception as e:
        log.debug(f"Tweet parse error: {e}")
        return None


def _extract_tweets_from_graphql(data) -> list[dict]:
    if not isinstance(data, dict):
        return []
    tweets: list[dict] = []
    try:
        instructions = (
            data.get("data", {})
                .get("search_by_raw_query", {})
                .get("search_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        for instruction in instructions:
            for entry in instruction.get("entries", []):
                content = entry.get("content", {})
                result  = content.get("itemContent", {}).get("tweet_results", {}).get("result")
                if result:
                    parsed = _parse_tweet_result(result)
                    if parsed:
                        tweets.append(parsed)
                for item in content.get("items", []):
                    result = item.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result")
                    if result:
                        parsed = _parse_tweet_result(result)
                        if parsed:
                            tweets.append(parsed)
    except Exception as e:
        log.debug(f"GraphQL parse error: {e}")
    return tweets


async def _login_x(page: Page):
    log.info("X: logging in...")
    await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(3)

    # Try to find username input with a generous timeout
    username_input = None
    for selector in ['input[name="text"]', 'input[autocomplete="username"]', 'input[type="text"]']:
        try:
            await page.wait_for_selector(selector, timeout=10_000)
            username_input = selector
            break
        except Exception:
            continue

    if username_input is None:
        await page.screenshot(path="/tmp/x_login_debug.png")
        log.error(f"X: username field not found. Page URL: {page.url}. Screenshot saved to /tmp/x_login_debug.png")
        return

    await page.click(username_input)
    await page.type(username_input, X_USERNAME, delay=80)
    await asyncio.sleep(1)
    await page.keyboard.press("Enter")
    await asyncio.sleep(2)

    # Handle second identity prompt (phone/email confirmation)
    try:
        second = page.locator('input[name="text"]')
        await second.wait_for(state="visible", timeout=4_000)
        log.info("X: handling second identity prompt")
        await second.clear()
        await second.type(X_USERNAME, delay=80)
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)
    except Exception:
        pass

    pw = None
    for locator in [
        page.locator('[autocomplete="current-password"]'),
        page.get_by_placeholder("Password"),
        page.locator('input[name="password"]'),
        page.locator('input[type="password"]'),
    ]:
        try:
            await locator.wait_for(state="visible", timeout=8_000)
            pw = locator
            break
        except Exception:
            continue

    if pw is None:
        await page.screenshot(path="/tmp/x_password_debug.png")
        log.error(f"X: password field not found. URL: {page.url}. Screenshot → /tmp/x_password_debug.png")
        return

    await pw.click()
    await pw.type(X_PASSWORD, delay=80)
    await asyncio.sleep(1)
    await page.keyboard.press("Enter")
    await asyncio.sleep(4)
    log.info(f"X: logged in — {page.url}")


async def scrape_x_async(limit_per_category: int = 10, on_tweet=None) -> list[dict]:
    """
    Scrape X for video tweets. If on_tweet(item) callback is provided,
    it is called immediately for each tweet found — no buffering.
    """
    results: list[dict] = []
    since = (datetime.now(timezone.utc).date() - timedelta(days=14)).isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        if X_USERNAME and X_PASSWORD:
            await _login_x(page)

        for event_type, queries in X_SEARCH_QUERIES.items():
            collected_ids: set[str] = set()
            category_count = 0

            for query in queries:
                if category_count >= limit_per_category:
                    break

                intercepted: list[dict] = []

                async def handle_response(resp: Response, _buf=intercepted):
                    if "SearchTimeline" in resp.url:
                        try:
                            _buf.extend(_extract_tweets_from_graphql(await resp.json()))
                        except Exception:
                            pass

                page.on("response", handle_response)
                dated_query = f"{query} since:{since}"
                log.info(f"X [{event_type}]: {dated_query[:80]}")
                try:
                    await page.goto(
                        f"https://x.com/search?q={quote_plus(dated_query)}&src=typed_query&f=video",
                        wait_until="domcontentloaded", timeout=30_000,
                    )
                    await asyncio.sleep(2)
                    for _ in range(20):
                        await page.evaluate("window.scrollBy(0, 1400)")
                        await asyncio.sleep(1.2)
                except Exception as e:
                    log.warning(f"  nav error: {e}")

                page.remove_listener("response", handle_response)

                for tweet in intercepted:
                    if category_count >= limit_per_category:
                        break
                    if tweet["tweet_id"] in collected_ids:
                        continue
                    collected_ids.add(tweet["tweet_id"])
                    tweet["platform"]   = "x"
                    tweet["event_type"] = event_type

                    # Process immediately if callback provided, otherwise buffer
                    if on_tweet:
                        on_tweet(tweet)
                    else:
                        results.append(tweet)

                    category_count += 1

                await asyncio.sleep(1)

            log.info(f"X [{event_type}]: {category_count} video tweets")

        await browser.close()

    log.info(f"X scrape done")
    return results


def scrape_x(limit_per_category: int = 10, on_tweet=None) -> list[dict]:
    return asyncio.run(scrape_x_async(limit_per_category, on_tweet=on_tweet))


# ─── Instagram scraper ───────────────────────────────────────────────────────

def scrape_instagram(limit_per_category: int = 5) -> list[dict]:
    loader = instaloader.Instaloader(
        download_videos=False, download_video_thumbnails=False,
        download_geotags=False, download_comments=False,
        save_metadata=False, quiet=True, request_timeout=30,
    )
    if IG_USERNAME and IG_PASSWORD:
        try:
            loader.login(IG_USERNAME, IG_PASSWORD)
            log.info("Instagram: authenticated")
        except Exception as e:
            log.warning(f"Instagram login failed: {e}")

    results: list[dict] = []
    for event_type, hashtags in IG_HASHTAGS.items():
        collected = 0
        for hashtag in hashtags:
            if collected >= limit_per_category:
                break
            try:
                tag = instaloader.Hashtag.from_name(loader.context, hashtag)
                for post in tag.get_posts_resumable():
                    if collected >= limit_per_category:
                        break
                    if not post.is_video or not post.video_url:
                        continue
                    results.append({
                        "platform":         "instagram",
                        "event_type":       event_type,
                        "tweet_id":         post.shortcode,
                        "text":             post.caption or "",
                        "url":              f"https://www.instagram.com/p/{post.shortcode}/",
                        "published_at":     post.date_utc.replace(tzinfo=timezone.utc),
                        "image_url":        post.url,
                        "video_url":        post.video_url,
                        "latitude":         post.location.lat if post.location else None,
                        "longitude":        post.location.lng if post.location else None,
                        "twitter_likes":    0,
                        "twitter_views":    post.video_view_count or 0,
                        "twitter_comments": post.comments,
                        "twitter_reposts":  0,
                    })
                    collected += 1
                    time.sleep(random.uniform(1, 2))
            except instaloader.exceptions.TooManyRequestsException:
                log.warning(f"Instagram: rate-limited on #{hashtag} — stopping")
                return results
            except Exception as e:
                log.warning(f"Instagram #{hashtag}: {e}")

        log.info(f"Instagram [{event_type}]: {collected} video posts")

    log.info(f"Instagram total: {len(results)}")
    return results


# ─── TikTok scraper ──────────────────────────────────────────────────────────

TIKTOK_SEARCH_QUERIES: dict[str, list[str]] = {
    "geopolitics": [
        "war conflict breaking news canada impact",
        "NATO Russia Ukraine war news english",
        "Middle East Israel Gaza war canada",
        "China Taiwan military tensions news",
        "geopolitics sanctions coup canada",
        "nuclear weapons threat news english",
    ],
    "trade_supply_chain": [
        "tariffs trade war canada impact news",
        "supply chain disruption canada news",
        "US China tariffs canada economy",
        "shipping port trade deal canada",
        "semiconductor shortage canada impact",
        "USMCA Canada trade news",
    ],
    "energy_commodities": [
        "oil price OPEC canada news",
        "natural gas LNG pipeline canada",
        "oil price breaking news canada economy",
        "energy crisis canada impact",
        "commodity prices canada news",
        "renewable energy canada transition",
    ],
    "financial_markets": [
        "stock market crash canada economy news",
        "interest rates Bank of Canada recession",
        "TSX stock market news canada",
        "Bank of Canada rate decision news",
        "crypto Bitcoin canada market",
        "inflation canada economy breaking news",
    ],
    "climate_disasters": [
        "hurricane earthquake flood breaking news",
        "wildfire canada BC Alberta disaster",
        "extreme weather canada emergency",
        "tornado disaster evacuation canada",
        "blizzard snowstorm canada warning",
        "flooding canada disaster news",
    ],
    "policy_regulation": [
        "canada government policy budget news",
        "canada parliament legislation news",
        "US policy canada impact news",
        "immigration canada border policy",
        "EU regulation canada impact news",
        "executive order canada trade impact",
    ],
}

# Trusted English news accounts to scrape directly (most reliable signal)
TIKTOK_NEWS_ACCOUNTS: list[tuple[str, str]] = [
    ("cbcnews",       "geopolitics"),
    ("globalnews",    "geopolitics"),
    ("ctvnews",       "policy_regulation"),
    ("reuters",       "geopolitics"),
    ("bbcnews",       "geopolitics"),
    ("cnni",          "climate_disasters"),
    ("abcnews",       "financial_markets"),
    ("bloombergbusiness", "financial_markets"),
    ("apnews",        "trade_supply_chain"),
    ("financialpost", "financial_markets"),
]


def _parse_tiktok_item(item: dict) -> Optional[dict]:
    try:
        if not isinstance(item, dict):
            return None
        video_id = item.get("id", "")
        if not video_id:
            return None

        desc = item.get("desc", "").strip()
        create_time = item.get("createTime", 0)
        try:
            published_at = datetime.fromtimestamp(int(create_time), tz=timezone.utc)
        except Exception:
            published_at = datetime.now(timezone.utc)

        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        if published_at < cutoff:
            return None

        video = item.get("video", {})
        video_url = None
        for field in ["playAddr", "downloadAddr", "playAddrH264"]:
            url = video.get(field, "")
            if url:
                video_url = url
                break
        if not video_url:
            return None

        image_url = video.get("dynamicCover") or video.get("cover") or video.get("originCover")

        stats  = item.get("stats", {})
        lat = lon = None
        poi = item.get("poi")
        if poi:
            lat = poi.get("latitude")
            lon = poi.get("longitude")

        author   = item.get("author", {})
        username = author.get("uniqueId", "unknown")

        return {
            "tweet_id":         video_id,
            "text":             desc,
            "url":              f"https://www.tiktok.com/@{username}/video/{video_id}",
            "published_at":     published_at,
            "image_url":        image_url,
            "video_url":        video_url,
            "latitude":         lat,
            "longitude":        lon,
            "twitter_likes":    stats.get("diggCount", 0),
            "twitter_views":    stats.get("playCount", 0),
            "twitter_comments": stats.get("commentCount", 0),
            "twitter_reposts":  stats.get("shareCount", 0),
        }
    except Exception as e:
        log.debug(f"TikTok parse error: {e}")
        return None




async def _upload_tiktok_media(item: dict, cookies: dict) -> dict:
    """Download TikTok video/thumb using browser cookies, upload to S3."""
    tid = item.get("tweet_id", str(uuid.uuid4()))
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/",
    }
    if item.get("video_url"):
        try:
            with httpx.Client(timeout=20, follow_redirects=True, cookies=cookies, headers=headers) as client:
                resp = client.get(item["video_url"])
                resp.raise_for_status()
            key = f"media/tiktok/{tid}.mp4"
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=resp.content, ContentType="video/mp4")
            item["video_url"] = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
            log.info(f"  TikTok Video → {item['video_url']}")
        except Exception as e:
            log.warning(f"  TikTok video upload failed: {e}")

    if item.get("image_url"):
        try:
            with httpx.Client(timeout=10, follow_redirects=True, headers=headers) as client:
                resp = client.get(item["image_url"])
                resp.raise_for_status()
            key = f"media/tiktok/{tid}_thumb.jpg"
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=resp.content, ContentType="image/jpeg")
            item["image_url"] = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
            log.info(f"  TikTok Thumb → {item['image_url']}")
        except Exception as e:
            log.warning(f"  TikTok thumb upload failed: {e}")

    return item


async def _login_tiktok(page: Page):
    log.info("TikTok: logging in...")
    await page.goto("https://www.tiktok.com/login/phone-or-email/email", wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(3)

    # Fill email/username
    email_input = None
    for selector in ['input[name="username"]', 'input[type="text"]', 'input[placeholder*="email" i]', 'input[placeholder*="username" i]']:
        try:
            await page.wait_for_selector(selector, timeout=6_000)
            email_input = selector
            break
        except Exception:
            continue

    if email_input is None:
        await page.screenshot(path="/tmp/tt_login_debug.png")
        log.error(f"TikTok: username field not found. Screenshot → /tmp/tt_login_debug.png")
        return

    await page.click(email_input)
    await page.type(email_input, TT_USERNAME, delay=80)
    await asyncio.sleep(0.5)

    # Fill password
    pw = None
    for selector in ['input[type="password"]', 'input[name="password"]', 'input[placeholder*="password" i]']:
        try:
            await page.wait_for_selector(selector, timeout=6_000)
            pw = selector
            break
        except Exception:
            continue

    if pw is None:
        await page.screenshot(path="/tmp/tt_pw_debug.png")
        log.error(f"TikTok: password field not found. Screenshot → /tmp/tt_pw_debug.png")
        return

    await page.click(pw)
    await page.type(pw, TT_PASSWORD, delay=80)
    await asyncio.sleep(0.5)
    await page.keyboard.press("Enter")
    await asyncio.sleep(3)

    # If 2FA / CAPTCHA is shown, wait for the user to complete it manually
    log.info("TikTok: waiting 30s for any 2FA/CAPTCHA — complete it in the browser now...")
    await asyncio.sleep(30)
    log.info(f"TikTok: login done — {page.url}")


def _parse_tiktok_page_data(raw_json: dict) -> Optional[dict]:
    """Extract video item from TikTok's __UNIVERSAL_DATA_FOR_REHYDRATION__ page JSON."""
    try:
        scope = raw_json.get("__DEFAULT_SCOPE__", {})
        detail = scope.get("webapp.video-detail", {})
        item = detail.get("itemInfo", {}).get("itemStruct")
        if not item:
            return None
        return _parse_tiktok_item(item)
    except Exception as e:
        log.debug(f"TikTok page data parse error: {e}")
        return None


async def _scrape_video_page(page: Page, url: str, event_type: str, cookies: dict) -> Optional[dict]:
    """Navigate to a single TikTok video page and extract its data."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        await asyncio.sleep(1.5)
        raw = await page.evaluate("""() => {
            const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
            return el ? el.textContent : null;
        }""")
        if not raw:
            return None
        parsed = _parse_tiktok_page_data(json.loads(raw))
        if parsed:
            parsed["platform"]   = "tiktok"
            parsed["event_type"] = event_type
            parsed = await _upload_tiktok_media(parsed, cookies)
        return parsed
    except Exception as e:
        log.debug(f"TikTok video page error {url}: {e}")
        return None


async def scrape_tiktok_async(limit_per_category: int = 10, on_tweet=None) -> list[dict]:
    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        if TT_USERNAME and TT_PASSWORD:
            await _login_tiktok(page)
        else:
            log.info("TikTok: no credentials — loading home page for session cookies...")
            await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(3)

        first_search = True
        for event_type, queries in TIKTOK_SEARCH_QUERIES.items():
            collected_ids: set[str] = set()
            category_count = 0

            for query in queries:
                if category_count >= limit_per_category:
                    break

                log.info(f"TikTok [{event_type}]: searching '{query[:60]}'")
                try:
                    await page.goto(
                        f"https://www.tiktok.com/search/video?q={quote_plus(query)}",
                        wait_until="domcontentloaded", timeout=30_000,
                    )
                    if first_search:
                        log.info("TikTok: pausing 10s — complete any CAPTCHA in the browser now...")
                        await asyncio.sleep(10)
                        first_search = False
                    await asyncio.sleep(2)
                    # Scroll to load more video thumbnails
                    for _ in range(10):
                        await page.evaluate("window.scrollBy(0, 1400)")
                        await asyncio.sleep(1.0)
                except Exception as e:
                    log.warning(f"  TikTok search nav error: {e}")
                    continue

                # Collect all video page links from the search grid
                hrefs = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href*="/video/"]'))
                        .map(a => a.href)
                        .filter(h => h.includes('/@') && h.includes('/video/'));
                }""")
                unique_hrefs = list(dict.fromkeys(hrefs))  # dedupe preserving order
                log.info(f"  Found {len(unique_hrefs)} video links on search page")

                cookies_list = await context.cookies()
                cookies = {c["name"]: c["value"] for c in cookies_list}

                for href in unique_hrefs:
                    if category_count >= limit_per_category:
                        break
                    # Extract video ID from URL to dedup
                    video_id = href.split("/video/")[-1].split("?")[0]
                    if video_id in collected_ids:
                        continue
                    collected_ids.add(video_id)

                    log.info(f"  → {href[:80]}")
                    item = await _scrape_video_page(page, href, event_type, cookies)
                    if item is None:
                        continue

                    if on_tweet:
                        on_tweet(item)
                    else:
                        results.append(item)

                    category_count += 1
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                await asyncio.sleep(1)

            log.info(f"TikTok [{event_type}]: {category_count} videos")

        # Scrape trusted news account profiles directly
        log.info("TikTok: scraping trusted news accounts...")
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        account_ids: set[str] = set()

        for username, event_type in TIKTOK_NEWS_ACCOUNTS:
            try:
                await page.goto(
                    f"https://www.tiktok.com/@{username}",
                    wait_until="domcontentloaded", timeout=20_000,
                )
                await asyncio.sleep(2)
                for _ in range(8):
                    await page.evaluate("window.scrollBy(0, 1400)")
                    await asyncio.sleep(1.0)

                hrefs = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href*="/video/"]'))
                        .map(a => a.href)
                        .filter(h => h.includes('/@') && h.includes('/video/'));
                }""")
                unique_hrefs = list(dict.fromkeys(hrefs))
                log.info(f"  @{username}: {len(unique_hrefs)} links found")

                cookies_list = await context.cookies()
                cookies = {c["name"]: c["value"] for c in cookies_list}

                collected = 0
                for href in unique_hrefs:
                    if collected >= limit_per_category:
                        break
                    video_id = href.split("/video/")[-1].split("?")[0]
                    if video_id in account_ids:
                        continue
                    account_ids.add(video_id)

                    item = await _scrape_video_page(page, href, event_type, cookies)
                    if item is None:
                        continue
                    if item["published_at"] < cutoff:
                        continue

                    if on_tweet:
                        on_tweet(item)
                    else:
                        results.append(item)

                    collected += 1
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                log.info(f"  @{username}: {collected} videos saved")
            except Exception as e:
                log.warning(f"  @{username} error: {e}")

        await browser.close()

    log.info("TikTok scrape done")
    return results


def scrape_tiktok(limit_per_category: int = 10, on_tweet=None) -> list[dict]:
    return asyncio.run(scrape_tiktok_async(limit_per_category, on_tweet=on_tweet))


# ─── Database helpers ────────────────────────────────────────────────────────

def upsert_source(cur, name, source_type, base_url, trust_score) -> int:
    cur.execute(
        """
        INSERT INTO sources (name, type, base_url, trust_score) VALUES (%s,%s,%s,%s)
        ON CONFLICT (name) DO UPDATE SET trust_score = EXCLUDED.trust_score
        RETURNING id
        """,
        (name, source_type, base_url, trust_score),
    )
    return cur.fetchone()["id"]


def insert_engagement(cur, *, twitter_likes, twitter_views, twitter_comments, twitter_reposts) -> str:
    eid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO engagement (id, twitter_likes, twitter_views, twitter_comments, twitter_reposts) "
        "VALUES (%s,%s,%s,%s,%s)",
        (eid, twitter_likes, twitter_views, twitter_comments, twitter_reposts),
    )
    return eid


def insert_content(cur, *, source_id, title, body, url, published_at,
                   image_url, latitude, longitude, engagement_id, event_type) -> Optional[str]:
    cid = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO content_table
            (id, source_id, title, body, url, published_at, image_url,
             latitude, longitude, engagement_id, event_type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """,
        (cid, source_id, title, body, url, published_at, image_url,
         latitude, longitude, engagement_id, event_type),
    )
    row = cur.fetchone()
    return row["id"] if row else None


def insert_event(cur, *, title, summary, event_type, primary_latitude, primary_longitude) -> str:
    eid = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO events (id, title, summary, event_type, primary_latitude, primary_longitude)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (eid, title, summary, event_type, primary_latitude, primary_longitude),
    )
    return cur.fetchone()["id"]


def link_event_content(cur, event_id, content_id):
    cur.execute(
        "INSERT INTO event_content (event_id, content_item_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
        (event_id, content_id),
    )


# ─── Pipeline ────────────────────────────────────────────────────────────────

class Pipeline:
    """
    Opens one DB connection for the whole scrape session.
    process(item) is called immediately for each tweet as it arrives.
    """

    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cur  = self.conn.cursor(cursor_factory=RealDictCursor)
        self.x_src  = upsert_source(self.cur, "X (Twitter)", "social_video", "https://x.com", 0.55)
        self.ig_src = upsert_source(self.cur, "Instagram",   "social_video", "https://www.instagram.com", 0.50)
        self.tt_src = upsert_source(self.cur, "TikTok",      "social_video", "https://www.tiktok.com", 0.45)
        self.conn.commit()
        self.inserted = 0
        self.skipped  = 0
        self.failed   = 0
        self.records  = []

    def process(self, item: dict):
        if not item.get("text", "").strip():
            self.skipped += 1
            return

        log.info(f"  → [{item['event_type']}] {item['url']}")
        try:
            # TikTok media is already uploaded inline during scraping — skip re-upload
            if item["platform"] != "tiktok":
                item = upload_media(item)
            title, body = split_title_body(item["text"])

            eng_id = insert_engagement(
                self.cur,
                twitter_likes=item["twitter_likes"],
                twitter_views=item["twitter_views"],
                twitter_comments=item["twitter_comments"],
                twitter_reposts=item["twitter_reposts"],
            )

            if item["platform"] == "x":
                source_id = self.x_src
            elif item["platform"] == "tiktok":
                source_id = self.tt_src
            else:
                source_id = self.ig_src
            # Prefer video S3 URL — that's the asset; fall back to thumbnail
            media_url = item.get("video_url") or item.get("image_url")

            content_id = insert_content(
                self.cur,
                source_id=source_id,
                title=title[:255],
                body=body,
                url=item["url"],
                published_at=item["published_at"],
                image_url=media_url,
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                engagement_id=eng_id,
                event_type=item["event_type"],
            )

            if content_id is None:
                log.info("    Duplicate — skipped")
                self.conn.rollback()
                self.skipped += 1
                return

            event_id = insert_event(
                self.cur,
                title=title[:255],
                summary=body,
                event_type=item["event_type"],
                primary_latitude=item.get("latitude"),
                primary_longitude=item.get("longitude"),
            )
            link_event_content(self.cur, event_id, content_id)
            self.conn.commit()
            self.inserted += 1
            log.info(f"    Saved event_id={event_id}")

            self.records.append({
                "event_id":    event_id,
                "content_id":  content_id,
                "platform":    item["platform"],
                "event_type":  item["event_type"],
                "title":       title,
                "body":        body,
                "url":         item["url"],
                "image_url":   item.get("image_url"),
                "video_url":   item.get("video_url"),
                "published_at": str(item["published_at"]),
                "engagement": {
                    "likes":    item["twitter_likes"],
                    "views":    item["twitter_views"],
                    "comments": item["twitter_comments"],
                    "reposts":  item["twitter_reposts"],
                },
            })

        except Exception as e:
            self.conn.rollback()
            log.error(f"    Failed: {e}")
            self.failed += 1

    def close(self):
        self.cur.close()
        self.conn.close()
        log.info(f"Pipeline closed — inserted={self.inserted} skipped={self.skipped} failed={self.failed}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape X/TikTok/Instagram → S3 + PostgreSQL")
    parser.add_argument("--platform", choices=["x", "tiktok", "instagram", "all"], default="all")
    parser.add_argument("--limit", type=int, default=10, help="Max videos per event category")
    parser.add_argument("--dry-run", action="store_true", help="Scrape only, skip S3+DB write")
    args = parser.parse_args()

    log.info(f"Starting — platform={args.platform}  limit={args.limit}/category")

    if args.dry_run:
        items: list[dict] = []
        if args.platform in ("x", "all"):
            items += scrape_x(limit_per_category=args.limit)
        if args.platform in ("tiktok", "all"):
            items += scrape_tiktok(limit_per_category=args.limit)
        if args.platform in ("instagram", "all"):
            items += scrape_instagram(limit_per_category=args.limit)
        print(json.dumps(items, indent=2, default=str))
        return

    # Live pipeline — each item is written to S3 + DB immediately as it arrives
    pipeline = Pipeline()
    try:
        if args.platform in ("x", "all"):
            scrape_x(limit_per_category=args.limit, on_tweet=pipeline.process)
        if args.platform in ("tiktok", "all"):
            scrape_tiktok(limit_per_category=args.limit, on_tweet=pipeline.process)
        if args.platform in ("instagram", "all"):
            for item in scrape_instagram(limit_per_category=args.limit):
                pipeline.process(item)
    finally:
        pipeline.close()

    print(json.dumps(pipeline.records, indent=2, default=str))


if __name__ == "__main__":
    main()
