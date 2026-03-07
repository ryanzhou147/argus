-- Migration: 001_init_schema.sql
-- Run with: psql $DATABASE_URL -f 001_init_schema.sql

BEGIN;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pgvector for embedding similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────
-- engagement (created first, referenced by content_table)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS engagement (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reddit_upvotes  INT DEFAULT 0,
    reddit_comments INT DEFAULT 0,
    poly_volume     FLOAT DEFAULT 0,
    poly_comments   INT DEFAULT 0,
    twitter_likes   INT DEFAULT 0,
    twitter_views   INT DEFAULT 0,
    twitter_comments INT DEFAULT 0,
    twitter_reposts INT DEFAULT 0
);

-- ─────────────────────────────────────────────
-- sources
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    type        TEXT,
    base_url    TEXT,
    trust_score FLOAT
);

-- ─────────────────────────────────────────────
-- content_table
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_table (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       INT REFERENCES sources(id) ON DELETE SET NULL,
    title           TEXT,
    body            TEXT,
    url             TEXT UNIQUE NOT NULL,
    published_at    TIMESTAMPTZ,
    latitude        FLOAT,
    longitude       FLOAT,
    engagement_id   UUID REFERENCES engagement(id) ON DELETE SET NULL,
    event_type      TEXT,
    embedding       vector(1536),   -- OpenAI text-embedding-3-small dim
    sentiment_score FLOAT,
    market_signal   FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- entities
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entities (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT,
    canonical_name TEXT,
    entity_type    TEXT   -- person, org, location, etc.
);

-- ─────────────────────────────────────────────
-- content_entities (join table)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_entities (
    content_item_id UUID REFERENCES content_table(id) ON DELETE CASCADE,
    entity_id       UUID REFERENCES entities(id) ON DELETE CASCADE,
    relevance_score FLOAT,
    PRIMARY KEY (content_item_id, entity_id)
);

-- ─────────────────────────────────────────────
-- events
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                 TEXT,
    summary               TEXT,
    event_type            TEXT,
    primary_latitude      FLOAT,
    primary_longitude     FLOAT,
    start_time            TIMESTAMPTZ,
    end_time              TIMESTAMPTZ,
    cluster_embedding     vector(1536),   -- OpenAI text-embedding-3-small dim
    canada_impact_summary TEXT,
    confidence_score      FLOAT
);

-- ─────────────────────────────────────────────
-- event_content (join table)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_content (
    event_id        UUID REFERENCES events(id) ON DELETE CASCADE,
    content_item_id UUID REFERENCES content_table(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, content_item_id)
);

-- ─────────────────────────────────────────────
-- event_relationships (graph edges)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_relationships (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_a_id        UUID REFERENCES events(id) ON DELETE CASCADE,
    event_b_id        UUID REFERENCES events(id) ON DELETE CASCADE,
    relationship_type TEXT,
    relationship_score FLOAT,
    reason_codes      TEXT[]
);

COMMIT;
