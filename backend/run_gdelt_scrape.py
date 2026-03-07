"""
Run GDELT scraper and persist results to the database.

Usage:
    venv2/bin/python run_gdelt_scrape.py              # last 14 days
    venv2/bin/python run_gdelt_scrape.py --days 7     # last 7 days
    venv2/bin/python run_gdelt_scrape.py --days 30    # last 30 days
    venv2/bin/python run_gdelt_scrape.py --dry-run    # fetch only, no DB write
"""
import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app.scrapers import gdelt
from app.services.scraping_service import fetch_and_persist_market_signals

parser = argparse.ArgumentParser(description="GDELT scraper")
parser.add_argument("--days", type=int, default=14, help="How many days back to scrape (default: 14)")
parser.add_argument("--limit", type=int, default=5000, help="Max rows to fetch (default: 5000)")
parser.add_argument("--dry-run", action="store_true", help="Fetch only, skip DB write")
args = parser.parse_args()

print(f"Scraping GDELT: last {args.days} days, limit {args.limit} rows")

rows = gdelt.fetch_all_rows(days=args.days, limit=args.limit)
print(f"Fetched {len(rows)} rows")

if args.dry_run:
    print("Dry run — not writing to DB")
    for r in rows[:5]:
        print(f"  {r['title'][:80]}")
        print(f"  {r['event_type']} | {r['url'][:70]}")
else:
    from app.services.scraping_service import persist_market_signals_to_db
    for r in rows:
        r["source"] = "gdelt"
    result = persist_market_signals_to_db(rows, verbose=True)
    if result:
        print(f"DB: {result[0]} engagement rows, {result[1]} content rows written")
    else:
        print("DB: skipped (DATABASE_URL not set)")
