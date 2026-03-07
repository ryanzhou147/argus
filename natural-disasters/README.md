# EONET Natural Disasters Scraper

Fetches natural disaster events from [NASA EONET API v2.1](https://eonet.gsfc.nasa.gov/docs/v2.1) and persists them into a local SQLite database that mirrors the production PostgreSQL schema.

## Schema mapping

| EONET field | DB table | DB column |
|---|---|---|
| `id` | `events` | `eonet_id` |
| `title` | `events` | `title` |
| `description` | `events` | `summary` |
| hardcoded | `events` | `event_type = "climate_disasters"` |
| first geometry coordinates | `events` | `primary_latitude`, `primary_longitude` |
| first geometry date | `events` | `start_time` |
| `closed` / last geometry date | `events` | `end_time` |
| `sources[].id` | `sources` | `name` |
| `sources[].url` | `content_table` | `url` |

## Setup

```bash
cd natural-disasters
python -m venv env
source env/bin/activate      # Windows: env\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
# Scrape last 14 days (default), all statuses
python scraper.py

# Scrape last 7 days, open events only
python scraper.py --days 7 --status open

# Scrape last 30 days, closed events only
python scraper.py --days 30 --status closed
```

Data is written to `eonet.db` in the same directory.

## Inspect results

```bash
sqlite3 eonet.db "SELECT id, title, event_type, primary_latitude, primary_longitude, start_time FROM events ORDER BY start_time DESC LIMIT 20;"
```
