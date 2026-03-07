"""
Polymarket scraper: fetch events by tag and normalize to a common row format.
"""
import json
import requests
from datetime import datetime

BASE_URL = "https://gamma-api.polymarket.com"

TARGET_TAGS = [
    "politics",
    "geopolitics",
    "foreign-policy",
    "macro-geopolitics",
    "economy",
    "economic-policy",
    "finance",
    "fed",
    "fed-rates",
    "commodities",
    "oil",
    "stocks",
    "ukraine",
    "ukraine-peace-deal",
    "middle-east",
    "israel",
    "iran",
    "military-strikes",
    "diplomacy-ceasefire",
    "gaza",
    "elections",
    "global-elections",
    "world-elections",
    "breaking-news",
    "climate-science",
    "science",
    "pandemics",
    "tech",
    "ai",
    "big-tech",
    "trump-presidency",
    "world",
    "world-affairs",
    "china",
    "ipos",
    "acquisitions",
    "business",
    "epstein",
    "canada",
]

EXCLUDE_TAGS = {
    "sports", "nba", "nfl", "nhl", "mlb", "soccer", "football", "basketball",
    "tennis", "golf", "hockey", "formula1", "f1", "atp", "champions-league",
    "la-liga", "EPL", "ligue-1", "ucl", "super-bowl", "stanley-cup",
    "world-series", "nba-finals", "nba-champion", "pga-tour", "the-masters",
    "hide-from-china", "hide-from-new", "rewards-20-4pt5-50", "rewards-200-3pt5-50",
    "all", "buy", "pre-market",
}


def fetch_events_by_tag(tag: str, limit: int = 500, offset: int = 0) -> list[dict]:
    params = {
        "limit": limit,
        "offset": offset,
        "active": "true",
        "closed": "false",
        "tag_slug": tag,
        "order": "volume",
        "ascending": "false",
    }
    resp = requests.get(f"{BASE_URL}/events", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_all_events(max_per_tag: int = 50) -> list[dict]:
    seen_ids = set()
    all_events = []

    for tag in TARGET_TAGS:
        try:
            events = fetch_events_by_tag(tag, limit=max_per_tag)
        except requests.RequestException:
            continue

        for event in events:
            eid = event.get("id")
            if eid in seen_ids:
                continue
            event_tag_slugs = {t["slug"] for t in event.get("tags", [])}
            if event_tag_slugs & EXCLUDE_TAGS:
                continue
            seen_ids.add(eid)
            all_events.append(event)

    return all_events


def _format_body(event: dict) -> str:
    description = (event.get("description") or "").strip()
    outcome_lines = []
    for market in event.get("markets", []):
        try:
            outcomes = json.loads(market.get("outcomes", "[]"))
            prices = json.loads(market.get("outcomePrices", "[]"))
        except (json.JSONDecodeError, TypeError):
            continue
        if not outcomes or not prices:
            continue
        parts = []
        for outcome, price in zip(outcomes, prices):
            try:
                pct = round(float(price) * 100, 1)
                parts.append(f"{outcome}: {pct}%")
            except (ValueError, TypeError):
                parts.append(f"{outcome}: ?%")
        label = market.get("groupItemTitle") or market.get("question", "")
        if len(event.get("markets", [])) == 1:
            outcome_lines.append(" | ".join(parts))
        else:
            outcome_lines.append(f"{label}: {' | '.join(parts)}")
    outcomes_str = "\n".join(outcome_lines)
    if description and outcomes_str:
        return f"{description}\n\nOutcomes:\n{outcomes_str}"
    if outcomes_str:
        return f"Outcomes:\n{outcomes_str}"
    return description or "No data"


def _event_to_engagement(event: dict) -> dict:
    return {
        "poly_volume": float(event.get("volume24hr") or 0),
        "poly_comments": int(event.get("commentCount") or 0),
    }


def event_to_row(event: dict) -> dict:
    slug = event.get("slug", "")
    url = f"https://polymarket.com/event/{slug}" if slug else ""
    published_at = None
    raw_date = event.get("startDate") or event.get("createdAt")
    if raw_date:
        try:
            published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    return {
        "title": event.get("title", "").strip(),
        "body": _format_body(event),
        "url": url,
        "published_at": published_at,
        "engagement": _event_to_engagement(event),
    }


def fetch_all_rows(max_per_tag: int = 50) -> list[dict]:
    """Fetch all Polymarket events and return normalized rows."""
    events = fetch_all_events(max_per_tag=max_per_tag)
    return [event_to_row(e) for e in events]
