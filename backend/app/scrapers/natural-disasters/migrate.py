"""
Migration script: SQLite (eonet.db) → AWS PostgreSQL
======================================================
Reads all scraped data from the local SQLite database and upserts it into
the production PostgreSQL schema. Safe to run multiple times (idempotent).

Usage:
    python migrate.py
    python migrate.py --dry-run   # connect and count rows without writing
"""
import argparse
import logging
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

_ENV_PATH = Path(__file__).parent / ".env"
_DB_PATH = Path(__file__).parent / "eonet.db"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_env() -> dict:
    if not _ENV_PATH.exists():
        raise FileNotFoundError(f".env not found at {_ENV_PATH}")
    cfg = {}
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def pg_connect(cfg: dict):
    return psycopg2.connect(
        host=cfg["PG_HOST"],
        port=int(cfg.get("PG_PORT", 5432)),
        user=cfg["PG_USER"],
        password=cfg["PG_PASSWORD"],
        dbname=cfg["PG_DB"],
    )


def sqlite_connect() -> sqlite3.Connection:
    if not _DB_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found at {_DB_PATH}. Run scraper.py first.")
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def migrate_sources(sqlite, pg, cur, dry_run: bool) -> int:
    rows = sqlite.execute("SELECT name, type, base_url, trust_score FROM sources").fetchall()
    if dry_run:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO sources (name, type, base_url, trust_score)
        VALUES %s
        ON CONFLICT (name) DO NOTHING
        """,
        [(r["name"], r["type"], r["base_url"], r["trust_score"]) for r in rows],
    )
    return len(rows)


def migrate_engagement(sqlite, pg, cur, dry_run: bool) -> int:
    rows = sqlite.execute(
        "SELECT id, reddit_upvotes, reddit_comments, poly_volume, poly_comments, "
        "twitter_likes, twitter_views, twitter_comments, twitter_reposts FROM engagement"
    ).fetchall()
    if dry_run or not rows:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO engagement
            (id, reddit_upvotes, reddit_comments, poly_volume, poly_comments,
             twitter_likes, twitter_views, twitter_comments, twitter_reposts)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        [tuple(r) for r in rows],
    )
    return len(rows)


def migrate_entities(sqlite, pg, cur, dry_run: bool) -> int:
    rows = sqlite.execute(
        "SELECT id, name, canonical_name, entity_type FROM entities"
    ).fetchall()
    if dry_run or not rows:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO entities (id, name, canonical_name, entity_type)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        [tuple(r) for r in rows],
    )
    return len(rows)


def migrate_content_table(sqlite, pg, cur, dry_run: bool) -> int:
    # Resolve source_id by name since Postgres auto-increments may differ
    source_map = {
        r[0]: r[1]
        for r in cur.execute("SELECT name, id FROM sources") or []
    }
    # Re-fetch from Postgres after sources insert
    cur.execute("SELECT name, id FROM sources")
    source_map = {r[0]: r[1] for r in cur.fetchall()}

    rows = sqlite.execute(
        """
        SELECT ct.id, s.name as source_name, ct.title, ct.body, ct.url,
               ct.published_at, ct.image_url, ct.latitude, ct.longitude,
               ct.engagement_id, ct.event_type, ct.sentiment_score,
               ct.market_signal, ct.created_at
        FROM content_table ct
        LEFT JOIN sources s ON s.id = ct.source_id
        """
    ).fetchall()
    if dry_run:
        return len(rows)

    values = []
    for r in rows:
        pg_source_id = source_map.get(r["source_name"])
        values.append((
            r["id"], pg_source_id, r["title"], r["body"], r["url"],
            r["published_at"], r["image_url"], r["latitude"], r["longitude"],
            r["engagement_id"], r["event_type"], r["sentiment_score"],
            r["market_signal"], r["created_at"],
        ))

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO content_table
            (id, source_id, title, body, url, published_at, image_url,
             latitude, longitude, engagement_id, event_type,
             sentiment_score, market_signal, created_at)
        VALUES %s
        ON CONFLICT (url) DO NOTHING
        """,
        values,
    )
    return len(rows)


def migrate_events(sqlite, pg, cur, dry_run: bool) -> int:
    # eonet_id is a SQLite-only dedup column — not in production schema, skip it
    rows = sqlite.execute(
        """
        SELECT id, title, summary, event_type, primary_latitude, primary_longitude,
               start_time, end_time, canada_impact_summary, confidence_score
        FROM events
        """
    ).fetchall()
    if dry_run:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO events
            (id, title, summary, event_type, primary_latitude, primary_longitude,
             start_time, end_time, canada_impact_summary, confidence_score)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        [tuple(r) for r in rows],
    )
    return len(rows)


def migrate_event_content(sqlite, pg, cur, dry_run: bool) -> int:
    rows = sqlite.execute(
        "SELECT event_id, content_item_id FROM event_content"
    ).fetchall()
    if dry_run or not rows:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO event_content (event_id, content_item_id)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        [tuple(r) for r in rows],
    )
    return len(rows)


def migrate_content_entities(sqlite, pg, cur, dry_run: bool) -> int:
    rows = sqlite.execute(
        "SELECT content_item_id, entity_id, relevance_score FROM content_entities"
    ).fetchall()
    if dry_run or not rows:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO content_entities (content_item_id, entity_id, relevance_score)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        [tuple(r) for r in rows],
    )
    return len(rows)


def migrate_event_relationships(sqlite, pg, cur, dry_run: bool) -> int:
    rows = sqlite.execute(
        "SELECT id, event_a_id, event_b_id, relationship_type, relationship_score, reason_codes "
        "FROM event_relationships"
    ).fetchall()
    if dry_run or not rows:
        return len(rows)
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO event_relationships
            (id, event_a_id, event_b_id, relationship_type, relationship_score, reason_codes)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        # reason_codes: stored as TEXT in SQLite, cast to TEXT[] in Postgres
        [(r["id"], r["event_a_id"], r["event_b_id"], r["relationship_type"],
          r["relationship_score"], r["reason_codes"]) for r in rows],
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate eonet.db to AWS PostgreSQL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Connect and count rows without writing anything")
    args = parser.parse_args()

    cfg = _load_env()
    sqlite = sqlite_connect()
    log.info("Connected to SQLite: %s", _DB_PATH)

    pg = pg_connect(cfg)
    pg.autocommit = False
    cur = pg.cursor()
    log.info("Connected to PostgreSQL: %s@%s/%s", cfg["PG_USER"], cfg["PG_HOST"], cfg["PG_DB"])

    if args.dry_run:
        log.info("DRY RUN — no data will be written")

    # Migrate in FK dependency order
    steps = [
        ("engagement",         migrate_engagement),
        ("sources",            migrate_sources),
        ("entities",           migrate_entities),
        ("content_table",      migrate_content_table),
        ("events",             migrate_events),
        ("event_content",      migrate_event_content),
        ("content_entities",   migrate_content_entities),
        ("event_relationships",migrate_event_relationships),
    ]

    try:
        for table, fn in steps:
            count = fn(sqlite, pg, cur, args.dry_run)
            log.info("%-25s %d rows %s", table, count,
                     "(dry run)" if args.dry_run else "migrated")

        if not args.dry_run:
            pg.commit()
            log.info("Migration committed successfully.")
        else:
            log.info("Dry run complete. No changes made.")

    except Exception as exc:
        pg.rollback()
        log.error("Migration failed, rolled back: %s", exc)
        raise
    finally:
        cur.close()
        pg.close()
        sqlite.close()


if __name__ == "__main__":
    main()
