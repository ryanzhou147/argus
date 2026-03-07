#!/usr/bin/env python3
"""Run Polymarket + Kalshi scrapers and persist to DB. Run from backend/ with venv2 active:
    source venv2/bin/activate && python run_scrape.py
"""
from dotenv import load_dotenv
load_dotenv()

from app.services.scraping_service import fetch_and_persist_market_signals

if __name__ == "__main__":
    print("Scrape starting...")
    rows, result = fetch_and_persist_market_signals(verbose=True)
    print(f"Done. Total rows: {len(rows)}")
    if result:
        print(f"DB write: {result[0]} engagement, {result[1]} content_table rows.")
    else:
        print("DB write: skipped (no DATABASE_URL or error).")
