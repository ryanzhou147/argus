"""
SQLite database setup mirroring the production PostgreSQL schema.
UUIDs stored as TEXT; vector columns omitted.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "eonet.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS engagement (
                id               TEXT PRIMARY KEY,
                reddit_upvotes   INTEGER DEFAULT 0,
                reddit_comments  INTEGER DEFAULT 0,
                poly_volume      REAL    DEFAULT 0,
                poly_comments    INTEGER DEFAULT 0,
                twitter_likes    INTEGER DEFAULT 0,
                twitter_views    INTEGER DEFAULT 0,
                twitter_comments INTEGER DEFAULT 0,
                twitter_reposts  INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sources (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT UNIQUE NOT NULL,
                type        TEXT,
                base_url    TEXT,
                trust_score REAL
            );

            CREATE TABLE IF NOT EXISTS content_table (
                id              TEXT PRIMARY KEY,
                source_id       INTEGER REFERENCES sources(id) ON DELETE SET NULL,
                title           TEXT,
                body            TEXT,
                url             TEXT UNIQUE NOT NULL,
                published_at    TEXT,
                image_url       TEXT,
                latitude        REAL,
                longitude       REAL,
                engagement_id   TEXT REFERENCES engagement(id) ON DELETE SET NULL,
                event_type      TEXT,
                sentiment_score REAL,
                market_signal   REAL,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS entities (
                id             TEXT PRIMARY KEY,
                name           TEXT,
                canonical_name TEXT,
                entity_type    TEXT
            );

            CREATE TABLE IF NOT EXISTS content_entities (
                content_item_id TEXT REFERENCES content_table(id) ON DELETE CASCADE,
                entity_id       TEXT REFERENCES entities(id) ON DELETE CASCADE,
                relevance_score REAL,
                PRIMARY KEY (content_item_id, entity_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id                    TEXT PRIMARY KEY,
                title                 TEXT,
                summary               TEXT,
                event_type            TEXT,
                primary_latitude      REAL,
                primary_longitude     REAL,
                start_time            TEXT,
                end_time              TEXT,
                canada_impact_summary TEXT,
                confidence_score      REAL,
                eonet_id              TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS event_content (
                event_id        TEXT REFERENCES events(id) ON DELETE CASCADE,
                content_item_id TEXT REFERENCES content_table(id) ON DELETE CASCADE,
                PRIMARY KEY (event_id, content_item_id)
            );

            CREATE TABLE IF NOT EXISTS event_relationships (
                id                 TEXT PRIMARY KEY,
                event_a_id         TEXT REFERENCES events(id) ON DELETE CASCADE,
                event_b_id         TEXT REFERENCES events(id) ON DELETE CASCADE,
                relationship_type  TEXT,
                relationship_score REAL,
                reason_codes       TEXT
            );
        """)
    conn.close()
