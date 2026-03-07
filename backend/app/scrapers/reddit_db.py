import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "reddit_scraper.db"
SCHEMA_PATH = Path(__file__).parent / "reddit_schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn):
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)


def get_or_create_source(conn, name, type_, base_url, trust_score):
    """Return the source id for the given name, inserting if it doesn't exist."""
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sources (name, type, base_url, trust_score) VALUES (?, ?, ?, ?)",
        (name, type_, base_url, trust_score),
    )
    conn.commit()
    return cursor.lastrowid


def upsert_post(cursor, post):
    """
    Insert engagement + content_table row in a single savepoint.
    Rolls back engagement insert if URL already exists to prevent orphaned rows.
    """
    cursor.execute("SAVEPOINT upsert_savepoint")

    cursor.execute(
        """
        INSERT INTO engagement (id, reddit_upvotes, reddit_comments)
        VALUES (?, ?, ?)
        """,
        (str(post["engagement_id"]), post["upvotes"], post["comments"]),
    )

    cursor.execute(
        """
        INSERT INTO content_table
            (id, source_id, title, body, url, published_at, image_url,
             engagement_id, event_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO NOTHING
        """,
        (
            str(post["id"]),
            post["source_id"],
            post["title"],
            post["body"],
            post["url"],
            post["published_at"].isoformat(),
            post["image_url"],
            str(post["engagement_id"]),
            post["event_type"],
        ),
    )

    rows_affected = cursor.rowcount
    if rows_affected == 0:
        cursor.execute("ROLLBACK TO SAVEPOINT upsert_savepoint")
        return False

    cursor.execute("RELEASE SAVEPOINT upsert_savepoint")
    return True
