"""
GDELT scraper: fetch Canada-relevant events via BigQuery (primary) or
GDELT DOC API (fallback, no credentials needed).

BigQuery path: requires `pip install google-cloud-bigquery` and either
  - GOOGLE_APPLICATION_CREDENTIALS env var pointing to a service account JSON, or
  - GDELT_GCP_PROJECT env var set to a GCP project (uses Application Default Credentials)
  Free tier: 1 TB queries/month — 14 days of filtered GDELT data is well under that.

DOC API path: pure HTTP, no credentials. Used automatically when BigQuery is unavailable.

Output rows are schema-aligned with 001_init_schema.sql (engagement + content_table).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .row_format import make_content_row

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = frozenset({
    "geopolitics",
    "trade_supply_chain",
    "energy_commodities",
    "financial_markets",
    "climate_disasters",
    "policy_regulation",
})

# CAMEO root code (2-digit) → event_type
CAMEO_ROOT_TO_EVENT_TYPE: dict[str, str] = {
    "01": "geopolitics",        # make public statement
    "02": "geopolitics",        # appeal
    "03": "geopolitics",        # express intent to cooperate
    "04": "policy_regulation",  # consult
    "05": "geopolitics",        # engage in diplomatic cooperation
    "06": "trade_supply_chain", # engage in material cooperation
    "07": "trade_supply_chain", # provide aid
    "08": "policy_regulation",  # yield / concede
    "09": "policy_regulation",  # investigate
    "10": "policy_regulation",  # demand
    "11": "policy_regulation",  # disapprove
    "12": "geopolitics",        # reject
    "13": "geopolitics",        # threaten
    "14": "geopolitics",        # protest
    "15": "geopolitics",        # exhibit military posture
    "16": "geopolitics",        # reduce relations
    "17": "geopolitics",        # coerce
    "18": "geopolitics",        # assault
    "19": "geopolitics",        # fight
    "20": "geopolitics",        # mass violence
}

# Human-readable verb per CAMEO root code for title construction
CAMEO_VERB: dict[str, str] = {
    "01": "made a statement about",
    "02": "appealed regarding",
    "03": "expressed intent to cooperate with",
    "04": "consulted with",
    "05": "cooperated diplomatically with",
    "06": "engaged in material cooperation with",
    "07": "provided aid to",
    "08": "yielded to",
    "09": "investigated",
    "10": "made demands of",
    "11": "disapproved of",
    "12": "rejected",
    "13": "threatened",
    "14": "protested against",
    "15": "exhibited military posture toward",
    "16": "reduced relations with",
    "17": "coerced",
    "18": "assaulted",
    "19": "fought with",
    "20": "committed mass violence against",
}

# Keywords in actor names that bump event_type to a more specific category
_ENERGY_KEYWORDS = {"oil", "gas", "energy", "petroleum", "opec", "lng", "pipeline", "coal"}
_FINANCIAL_KEYWORDS = {"bank", "fed", "finance", "imf", "treasury", "stock", "market", "trade"}
_CLIMATE_KEYWORDS = {"climate", "flood", "earthquake", "hurricane", "wildfire", "drought", "disaster"}


def _refine_event_type(base_type: str, actor1: str, actor2: str, geo: str) -> str:
    """Override base_type if actor/geo names strongly signal a specific category."""
    combined = f"{actor1} {actor2} {geo}".lower()
    if any(k in combined for k in _CLIMATE_KEYWORDS):
        return "climate_disasters"
    if any(k in combined for k in _ENERGY_KEYWORDS):
        return "energy_commodities"
    if any(k in combined for k in _FINANCIAL_KEYWORDS):
        return "financial_markets"
    return base_type


def _event_type_from_cameo(event_root_code: str, actor1: str, actor2: str, geo: str) -> str | None:
    root = (event_root_code or "")[:2]
    base = CAMEO_ROOT_TO_EVENT_TYPE.get(root)
    if base is None:
        return None
    refined = _refine_event_type(base, actor1, actor2, geo)
    return refined if refined in VALID_EVENT_TYPES else base


def _build_title(actor1: str, actor2: str, event_root_code: str, geo: str) -> str:
    root = (event_root_code or "")[:2]
    verb = CAMEO_VERB.get(root, "was involved in an event with")
    a1 = actor1.strip() or "Unknown actor"
    if actor2.strip():
        return f"{a1} {verb} {actor2.strip()}"
    if geo.strip():
        return f"{a1} {verb} in {geo.strip()}"
    return f"{a1}: {verb.replace('with', '').replace('of', '').strip()}"


def _parse_sqldate(sqldate: str | int) -> datetime | None:
    try:
        return datetime.strptime(str(sqldate)[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


_GOLDSTEIN_LABEL = [
    (-7.0, "highly destabilizing"),
    (-3.0, "destabilizing"),
    (-0.5, "mildly destabilizing"),
    ( 0.5, "neutral"),
    ( 3.0, "mildly stabilizing"),
    ( 7.0, "stabilizing"),
    ( 10.1, "highly stabilizing"),
]

def _goldstein_label(score: float) -> str:
    for threshold, label in _GOLDSTEIN_LABEL:
        if score < threshold:
            return label
    return "highly stabilizing"


def _row_from_bq(record: dict) -> dict:
    actor1 = str(record.get("Actor1Name") or "")
    actor2 = str(record.get("Actor2Name") or "")
    actor1_country = str(record.get("Actor1CountryCode") or "")
    actor2_country = str(record.get("Actor2CountryCode") or "")
    geo = str(record.get("ActionGeo_FullName") or "")
    event_root = str(record.get("EventRootCode") or "")
    num_mentions = record.get("NumMentions")
    goldstein = record.get("GoldsteinScale")
    avg_tone = record.get("AvgTone")

    title = _build_title(actor1, actor2, event_root, geo)

    # Build prose body
    root = (event_root or "")[:2]
    verb = CAMEO_VERB.get(root, "was involved in an event with")
    a1 = actor1.strip() or "An unknown actor"
    a1_ctx = f"{a1} ({actor1_country})" if actor1_country else a1

    sentences = []

    # Lead sentence: who did what to whom
    if actor2.strip():
        a2_ctx = f"{actor2.strip()} ({actor2_country})" if actor2_country else actor2.strip()
        sentences.append(f"{a1_ctx} {verb} {a2_ctx}.")
    elif geo.strip():
        sentences.append(f"{a1_ctx} {verb} in {geo.strip()}.")
    else:
        sentences.append(f"{a1_ctx} {verb.rstrip()}.")

    # Location context
    if geo:
        sentences.append(f"This event took place in {geo}.")

    # Actor country context if both actors present
    if actor1_country and actor2_country and actor1_country != actor2_country:
        sentences.append(f"Involves actors from {actor1_country} and {actor2_country}.")
    elif actor1_country and not actor2.strip():
        sentences.append(f"Primary actor country: {actor1_country}.")

    # Stability assessment
    if goldstein is not None:
        try:
            g = float(goldstein)
            sentences.append(
                f"Event assessed as {_goldstein_label(g)} on the Goldstein conflict scale ({g:+.1f}/10)."
            )
        except (TypeError, ValueError):
            pass

    # Tone context
    if avg_tone is not None:
        try:
            tone = float(avg_tone)
            tone_desc = "positive" if tone > 1 else "negative" if tone < -1 else "neutral"
            sentences.append(f"Media coverage tone is {tone_desc} ({tone:+.2f}).")
        except (TypeError, ValueError):
            pass

    # Coverage breadth
    if num_mentions:
        sentences.append(f"Reported across {num_mentions} news article mentions.")

    body = " ".join(sentences) if sentences else "No details available."

    url = str(record.get("SOURCEURL") or "").strip()
    published_at = _parse_sqldate(record.get("SQLDATE"))

    lat = record.get("ActionGeo_Lat")
    lon = record.get("ActionGeo_Long")
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        lat = lon = None

    # Normalize GoldsteinScale (-10..10) to -1..1 as market_signal
    market_signal = None
    if goldstein is not None:
        try:
            market_signal = max(-1.0, min(1.0, float(goldstein) / 10.0))
        except (TypeError, ValueError):
            pass

    # Normalize AvgTone (roughly -100..100) to -1..1 as sentiment_score
    sentiment_score = None
    if avg_tone is not None:
        try:
            sentiment_score = max(-1.0, min(1.0, float(avg_tone) / 10.0))
        except (TypeError, ValueError):
            pass

    event_type = _event_type_from_cameo(event_root, actor1, actor2, geo)

    return make_content_row(
        source="gdelt",
        title=title,
        body=body,
        url=url,
        published_at=published_at,
        image_url=None,
        latitude=lat,
        longitude=lon,
        event_type=event_type,
        sentiment_score=sentiment_score,
        market_signal=market_signal,
        engagement={},
    )


# ---------------------------------------------------------------------------
# BigQuery path
# ---------------------------------------------------------------------------

_BIGQUERY_QUERY = """
SELECT
    CAST(SQLDATE AS STRING)   AS SQLDATE,
    Actor1Name,
    Actor1CountryCode,
    Actor2Name,
    Actor2CountryCode,
    EventCode,
    EventRootCode,
    GoldsteinScale,
    NumMentions,
    AvgTone,
    ActionGeo_FullName,
    ActionGeo_CountryCode,
    ActionGeo_Lat,
    ActionGeo_Long,
    SOURCEURL
FROM `gdelt-bq.gdeltv2.events`
WHERE SQLDATE >= CAST(FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)) AS INT64)
  -- Only include CAMEO root codes that map to our event types (excludes sports/entertainment)
  AND EventRootCode IN ('01','02','03','04','05','06','07','08','09','10',
                        '11','12','13','14','15','16','17','18','19','20')
  -- Require at least one real country-level actor to filter out pop culture noise
  AND (Actor1CountryCode IS NOT NULL OR Actor2CountryCode IS NOT NULL)
  -- Minimum mention threshold to filter out single-article noise
  AND NumMentions >= 5
  AND SOURCEURL IS NOT NULL
  AND SOURCEURL != ''
ORDER BY NumMentions DESC
{limit_clause}
"""


def fetch_via_bigquery(days: int = 14, limit: int | None = None) -> list[dict]:
    """
    Query GDELT via BigQuery. Returns normalized rows or raises on any error.

    Requires:
      pip install google-cloud-bigquery
      GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
      (or GDELT_GCP_PROJECT set and Application Default Credentials configured)
    """
    try:
        from google.cloud import bigquery  # type: ignore[import]
    except ImportError:
        raise RuntimeError("google-cloud-bigquery not installed; run: pip install google-cloud-bigquery")

    project = os.environ.get("GDELT_GCP_PROJECT")
    client = bigquery.Client(project=project) if project else bigquery.Client()

    limit_clause = f"LIMIT {limit}" if limit is not None else ""
    sql = _BIGQUERY_QUERY.format(days=days, limit_clause=limit_clause)
    query_job = client.query(sql)
    results = query_job.result()

    rows = []
    for record in results:
        row_dict = dict(record)
        url = (row_dict.get("SOURCEURL") or "").strip()
        if not url:
            continue
        rows.append(_row_from_bq(row_dict))

    return rows


# ---------------------------------------------------------------------------
# DOC API fallback (no credentials, keyword search)
# ---------------------------------------------------------------------------

_DOC_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# Search queries per event_type — broad global coverage, no sports/entertainment
_DOC_QUERIES: dict[str, str] = {
    "geopolitics":        "diplomacy OR sanctions OR military OR war OR ceasefire OR NATO OR UN OR coup OR conflict",
    "trade_supply_chain": "trade OR tariffs OR supply chain OR imports OR exports OR WTO OR shipping OR logistics",
    "energy_commodities": "oil OR gas OR energy OR pipeline OR LNG OR commodities OR OPEC OR uranium OR mining",
    "financial_markets":  "economy OR GDP OR inflation OR interest rates OR central bank OR stock market OR recession OR currency",
    "climate_disasters":  "wildfire OR flood OR earthquake OR hurricane OR typhoon OR climate OR disaster OR drought",
    "policy_regulation":  "legislation OR regulation OR policy OR sanctions OR treaty OR bill OR law OR government",
}


def _doc_api_fetch(query: str, start_dt: datetime, end_dt: datetime, max_records: int = 50) -> list[dict]:
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_records,
        "format": "json",
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
        "sourcelang": "english",
    }
    resp = requests.get(_DOC_API_BASE, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("articles") or []


def _row_from_doc_article(article: dict, event_type: str) -> dict | None:
    url = (article.get("url") or "").strip()
    if not url:
        return None

    title = (article.get("title") or "").strip()
    if not title:
        title = f"GDELT: {event_type.replace('_', ' ').title()} event"

    # seendate format: "20260307T120000Z"
    published_at = None
    raw_date = article.get("seendate") or ""
    try:
        published_at = datetime.strptime(raw_date[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass

    tone_raw = article.get("tone")
    sentiment_score = None
    if tone_raw is not None:
        try:
            sentiment_score = max(-1.0, min(1.0, float(tone_raw) / 10.0))
        except (TypeError, ValueError):
            pass

    domain = article.get("domain") or ""
    source_country = article.get("sourcecountry") or ""
    body = f"Source: {domain}"
    if source_country:
        body += f" ({source_country})"

    return make_content_row(
        source="gdelt",
        title=title,
        body=body,
        url=url,
        published_at=published_at,
        image_url=None,
        latitude=None,
        longitude=None,
        event_type=event_type,
        sentiment_score=sentiment_score,
        market_signal=None,
        engagement={},
    )


def fetch_via_doc_api(days: int = 14, max_per_category: int = 50) -> list[dict]:
    """
    Fetch Canada-relevant GDELT articles via the DOC API. No credentials needed.
    Searches each event_type category separately and deduplicates by URL.
    """
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)

    seen_urls: set[str] = set()
    rows: list[dict] = []

    for i, (event_type, query) in enumerate(_DOC_QUERIES.items()):
        if i > 0:
            time.sleep(6)  # DOC API rate limit: 1 request per 5 seconds
        try:
            articles = _doc_api_fetch(query, start_dt, end_dt, max_records=max_per_category)
        except Exception:
            continue
        for article in articles:
            url = (article.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            row = _row_from_doc_article(article, event_type)
            if row:
                rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fetch_all_rows(days: int = 14, limit: int | None = 5000) -> list[dict]:
    """
    Fetch GDELT events for the past `days` days.

    Tries BigQuery first (structured data with lat/long, CAMEO event types,
    Goldstein scale). Falls back to the GDELT DOC API if BigQuery is not
    configured or google-cloud-bigquery is not installed.

    limit=None means no row cap (fetch everything matching the filters).
    """
    try:
        rows = fetch_via_bigquery(days=days, limit=limit)
        if rows:
            return rows
    except Exception:
        pass

    max_per_category = 100 if limit is None else min(limit // len(_DOC_QUERIES), 100)
    return fetch_via_doc_api(days=days, max_per_category=max_per_category)
