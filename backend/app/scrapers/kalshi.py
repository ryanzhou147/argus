"""
Kalshi scraper: fetch open events/markets and normalize to a common row format.
"""
import time
import requests
from datetime import datetime
from collections import defaultdict

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

TARGET_CATEGORIES = {
    "Politics",
    "Economics",
    "World",
    "Elections",
    "Companies",
    "Financials",
    "Science and Technology",
    "Health",
    "Climate and Weather",
    "Transportation",
}


def _paginate(endpoint: str, result_key: str, params: dict) -> list[dict]:
    results = []
    cursor = None
    while True:
        p = {**params}
        if cursor:
            p["cursor"] = cursor
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=p, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get(result_key, [])
        results.extend(batch)
        cursor = data.get("cursor") or None
        if not cursor or not batch:
            break
        time.sleep(0.05)
    return results


def fetch_event_map() -> dict[str, dict]:
    all_events = _paginate("events", "events", {"status": "open", "limit": 200})
    return {
        e["event_ticker"]: e
        for e in all_events
        if e.get("category") in TARGET_CATEGORIES
    }


def fetch_all_markets() -> list[dict]:
    return _paginate("markets", "markets", {"status": "open", "limit": 1000})


def _format_body(markets: list[dict]) -> str:
    description = ""
    for m in markets:
        rules = (m.get("rules_primary") or "").strip()
        if rules:
            description = rules
            break
    outcome_lines = []
    for market in markets:
        yes_price = market.get("yes_bid") or market.get("yes_ask") or 0
        no_price = 100 - yes_price
        yes_pct = round(float(yes_price), 1)
        no_pct = round(float(no_price), 1)
        if len(markets) == 1:
            outcome_lines.append(f"Yes: {yes_pct}% | No: {no_pct}%")
        else:
            label = (market.get("subtitle") or market.get("title") or "").strip()
            outcome_lines.append(f"{label}: Yes: {yes_pct}% | No: {no_pct}%")
    outcomes_str = "\n".join(outcome_lines)
    if description and outcomes_str:
        return f"{description}\n\nOutcomes:\n{outcomes_str}"
    if outcomes_str:
        return f"Outcomes:\n{outcomes_str}"
    return description or "No data"


def event_to_row(event: dict, markets: list[dict]) -> dict:
    event_ticker = event.get("event_ticker", "")
    url = f"https://kalshi.com/markets/{event_ticker}" if event_ticker else ""
    published_at = None
    raw_date = event.get("last_updated_ts")
    if raw_date:
        try:
            published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    title = event.get("title", "").strip()
    sub_title = event.get("sub_title", "").strip()
    if sub_title and sub_title not in title:
        title = f"{title} ({sub_title})"
    total_volume_24h = sum(float(m.get("volume_24h") or 0) for m in markets)
    return {
        "title": title,
        "body": _format_body(markets),
        "url": url,
        "published_at": published_at,
        "engagement": {
            "poly_volume": total_volume_24h,
            "poly_comments": None,
        },
    }


def fetch_all_rows() -> list[dict]:
    """Fetch all Kalshi events in target categories and return normalized rows."""
    event_map = fetch_event_map()
    all_markets = fetch_all_markets()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for market in all_markets:
        et = market.get("event_ticker")
        if et in event_map:
            grouped[et].append(market)
    rows = []
    for event_ticker, markets in grouped.items():
        event = event_map[event_ticker]
        rows.append(event_to_row(event, markets))
    rows.sort(key=lambda r: r["engagement"]["poly_volume"], reverse=True)
    return rows
