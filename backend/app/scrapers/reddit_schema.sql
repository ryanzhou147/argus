-- SQLite adaptation of 001_init_schema.sql
-- (pgcrypto/pgvector extensions, SERIAL, UUID, TIMESTAMPTZ, TEXT[] → SQLite equivalents)

CREATE TABLE IF NOT EXISTS engagement (
    id               TEXT    PRIMARY KEY,
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
    id              TEXT    PRIMARY KEY,
    source_id       INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    title           TEXT,
    body            TEXT,
    url             TEXT UNIQUE NOT NULL,
    published_at    TEXT,
    image_url       TEXT,
    latitude        REAL,
    longitude       REAL,
    engagement_id   TEXT    REFERENCES engagement(id) ON DELETE SET NULL,
    event_type      TEXT    CHECK (event_type IN (
                        'geopolitics', 'trade_supply_chain', 'energy_commodities',
                        'financial_markets', 'climate_disasters', 'policy_regulation'
                    )),
    embedding       TEXT,           -- placeholder; vector(1536) not supported in SQLite
    sentiment_score REAL,
    market_signal   REAL,
    created_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
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
    cluster_embedding     TEXT,     -- placeholder; vector(1536) not supported in SQLite
    canada_impact_summary TEXT,
    confidence_score      REAL
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
    reason_codes       TEXT        -- JSON array (TEXT[] not supported in SQLite)
);

CREATE INDEX IF NOT EXISTS idx_content_published_at ON content_table (published_at);
CREATE INDEX IF NOT EXISTS idx_content_event_type   ON content_table (event_type);
CREATE INDEX IF NOT EXISTS idx_content_source_id    ON content_table (source_id);
