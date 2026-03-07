"""
Kalshi scraper: fetch open events/markets and normalize to a common row format.

Optimized to filter server-side: fetch markets per event (event_ticker param)
instead of all markets, and use asyncio with a 10 req/sec rate limit to batch
~10 events at a time.
"""
import asyncio
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx
import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
RATE_LIMIT_PER_SEC = 10

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


# ---------------------------------------------------------------------------
# Sync: events only (used once to get event_tickers we care about)
# ---------------------------------------------------------------------------

def _paginate_sync(endpoint: str, result_key: str, params: dict[str, Any]) -> list[dict]:
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
        time.sleep(0.1)
    return results


def fetch_event_map() -> dict[str, dict]:
    """Return {event_ticker: event_dict} for open events in target categories."""
    all_events = _paginate_sync("events", "events", {"status": "open", "limit": 200})
    return {
        e["event_ticker"]: e
        for e in all_events
        if e.get("category") in TARGET_CATEGORIES
    }


# ---------------------------------------------------------------------------
# Async: markets per event with rate limiting (10 req/sec)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Allows at most `rate` requests per `period` seconds."""

    def __init__(self, rate: int = RATE_LIMIT_PER_SEC, period: float = 1.0) -> None:
        self.rate = rate
        self.period = period
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self.period]
            while len(self._timestamps) >= self.rate:
                wait = self.period - (now - self._timestamps[0])
                if wait > 0:
                    await asyncio.sleep(wait)
                    now = time.monotonic()
                    self._timestamps = [t for t in self._timestamps if now - t < self.period]
            self._timestamps.append(now)


async def _fetch_markets_for_event(
    client: httpx.AsyncClient,
    limiter: _RateLimiter,
    event_ticker: str,
) -> tuple[str, list[dict]]:
    """Fetch all pages of markets for one event. Server-side filter via event_ticker."""
    results: list[dict] = []
    cursor: str | None = None
    while True:
        await limiter.acquire()
        params: dict[str, Any] = {
            "status": "open",
            "event_ticker": event_ticker,
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor
        resp = await client.get(f"{BASE_URL}/markets", params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("markets", [])
        results.extend(batch)
        cursor = data.get("cursor")
        if not cursor or not batch:
            break
    return (event_ticker, results)


async def _fetch_all_markets_for_events(event_tickers: list[str]) -> dict[str, list[dict]]:
    """Fetch markets for each event concurrently; rate limit 10 req/sec across all."""
    limiter = _RateLimiter(rate=RATE_LIMIT_PER_SEC, period=1.0)
    grouped: dict[str, list[dict]] = defaultdict(list)
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_markets_for_event(client, limiter, et) for et in event_tickers]
        pairs = await asyncio.gather(*tasks, return_exceptions=True)
    for p in pairs:
        if isinstance(p, Exception):
            continue
        event_ticker, markets = p
        grouped[event_ticker] = markets
    return dict(grouped)


# ---------------------------------------------------------------------------
# Formatting (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main entry: fetch events (sync), then markets per event (async, rate-limited)
# ---------------------------------------------------------------------------

def fetch_all_rows(max_events: int | None = None) -> list[dict]:
    """
    Fetch Kalshi events in target categories, then fetch markets per event
    (server-side filter) with asyncio and 10 req/sec rate limit. Skips the
    slow "fetch all markets" approach.

    Pass max_events to cap the number of events (e.g. for testing).
    """
    event_map = fetch_event_map()
    event_tickers = list(event_map.keys())
    if max_events is not None:
        event_tickers = event_tickers[:max_events]
    if not event_tickers:
        return []

    grouped = asyncio.run(_fetch_all_markets_for_events(event_tickers))

    rows = []
    for event_ticker, markets in grouped.items():
        event = event_map.get(event_ticker)
        if not event or not markets:
            continue
        rows.append(event_to_row(event, markets))

    rows.sort(key=lambda r: r["engagement"]["poly_volume"], reverse=True)
    return rows
