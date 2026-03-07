"""
Quick database inspector — shows a human-readable summary of eonet.db.

Usage:
    python inspect_db.py              # summary + 10 most recent events
    python inspect_db.py --full       # show all events
    python inspect_db.py --event <id> # detail for one event (eonet id or uuid)
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# Force UTF-8 output on Windows so box-drawing chars render correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "eonet.db"


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def fmt(val, width=None):
    s = str(val) if val is not None else "—"
    if width:
        return s[:width].ljust(width)
    return s


def print_counts(db):
    print("\n── TABLE COUNTS ─────────────────────────────────")
    tables = ["events", "sources", "content_table", "event_content",
              "engagement", "entities", "content_entities", "event_relationships"]
    for t in tables:
        n = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<25} {n:>5} rows")


def print_sources(db):
    print("\n── SOURCES ──────────────────────────────────────")
    rows = db.execute("SELECT name, type, base_url, trust_score FROM sources ORDER BY name").fetchall()
    for r in rows:
        print(f"  {fmt(r['name'], 16)}  {fmt(r['base_url'])}")


def print_events(db, limit=10):
    label = f"last {limit}" if limit else "all"
    print(f"\n── EVENTS ({label}, newest first) ──────────────")
    header = f"  {'eonet_id':<16} {'title':<50} {'lat':>8} {'lon':>9}  {'start_time':<25} {'open?'}"
    print(header)
    print("  " + "─" * (len(header) - 2))
    q = "SELECT eonet_id, title, primary_latitude, primary_longitude, start_time, end_time FROM events ORDER BY start_time DESC"
    if limit:
        q += f" LIMIT {limit}"
    for r in db.execute(q):
        is_open = "open" if r["end_time"] is None else "closed"
        lat = f"{r['primary_latitude']:.2f}" if r["primary_latitude"] is not None else "—"
        lon = f"{r['primary_longitude']:.2f}" if r["primary_longitude"] is not None else "—"
        print(f"  {fmt(r['eonet_id'], 16)} {fmt(r['title'], 50)} {lat:>8} {lon:>9}  {fmt(r['start_time'], 25)} {is_open}")


def print_event_detail(db, event_ref: str):
    row = db.execute(
        "SELECT * FROM events WHERE eonet_id = ? OR id = ?", (event_ref, event_ref)
    ).fetchone()
    if not row:
        print(f"Event '{event_ref}' not found.")
        return

    print(f"\n── EVENT DETAIL ─────────────────────────────────")
    for key in row.keys():
        print(f"  {key:<25} {fmt(row[key])}")

    # Linked content items
    content = db.execute(
        """
        SELECT ct.url, ct.published_at, s.name as source_name
        FROM event_content ec
        JOIN content_table ct ON ct.id = ec.content_item_id
        LEFT JOIN sources s ON s.id = ct.source_id
        WHERE ec.event_id = ?
        """,
        (row["id"],),
    ).fetchall()
    if content:
        print(f"\n  Linked content items ({len(content)}):")
        for c in content:
            print(f"    [{fmt(c['source_name'])}] {c['url']}")


def print_null_coverage(db):
    print("\n── NULL COVERAGE (events table) ─────────────────")
    total = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if total == 0:
        print("  No events.")
        return
    cols = ["title", "summary", "event_type", "primary_latitude", "primary_longitude",
            "start_time", "end_time", "canada_impact_summary", "confidence_score"]
    for col in cols:
        filled = db.execute(f"SELECT COUNT(*) FROM events WHERE {col} IS NOT NULL").fetchone()[0]
        pct = filled / total * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {col:<26} {bar} {filled:>4}/{total} ({pct:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="Inspect eonet.db")
    parser.add_argument("--full", action="store_true", help="Show all events (not just 10)")
    parser.add_argument("--event", metavar="ID", help="Show detail for one event (eonet_id or uuid)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run scraper.py first.")
        return

    db = conn()
    print(f"\nDatabase: {DB_PATH}")

    if args.event:
        print_event_detail(db, args.event)
    else:
        print_counts(db)
        print_sources(db)
        print_null_coverage(db)
        print_events(db, limit=0 if args.full else 10)

    db.close()


if __name__ == "__main__":
    main()
