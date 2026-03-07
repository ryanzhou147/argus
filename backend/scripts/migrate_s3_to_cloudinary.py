"""
Migrate all S3 media in the hackcanada bucket to Cloudinary.

S3 bucket structure:
  media/tiktok/{id}.{ext}          → Cloudinary: hackcanada/tiktok/{id}
  media/x/{id}.{ext}               → Cloudinary: hackcanada/x/{id}
  images/2026/03/07/{source}/{id}/{file.ext} → Cloudinary: hackcanada/news/{source}/{id}

For each file the script:
  1. Extracts the content ID and source from the S3 key.
  2. Builds a presigned GET URL (bucket is private).
  3. Uploads to Cloudinary with a 720x720 fill eager transform.
  4. Looks up the matching content_table row:
       - First by image_url containing the S3 URL.
       - Then by content_table.id matching the extracted ID.
  5. Updates content_table: image_url → Cloudinary public_id, s3_url → original S3 URL.

Idempotent: rows that already have s3_url set are skipped at query time.
Safe to re-run at any time.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path, PurePosixPath

# Load backend/.env automatically
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

import cloudinary
import cloudinary.uploader
import boto3
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi"}

# S3 prefixes to scan
SCAN_PREFIXES = ["media/tiktok/", "media/x/", "images/"]

# Skip "folder" placeholder objects (keys that end with /)
def is_real_file(key: str) -> bool:
    return not key.endswith("/") and PurePosixPath(key).suffix != ""


def classify_key(key: str) -> tuple[str, str] | None:
    """
    Returns (cloudinary_public_id, content_id_hint) for a given S3 key, or None if unrecognised.

    Path rules:
      media/tiktok/{id}.ext           → public_id = hackcanada/tiktok/{id}
      media/x/{id}.ext                → public_id = hackcanada/x/{id}
      images/**/{source}/{id}/{file}  → public_id = hackcanada/news/{source}/{id}
    """
    parts = key.split("/")
    p = PurePosixPath(key)

    if key.startswith("media/tiktok/") and len(parts) == 3:
        content_id = p.stem
        return f"hackcanada/tiktok/{content_id}", content_id

    if key.startswith("media/x/") and len(parts) == 3:
        content_id = p.stem
        return f"hackcanada/x/{content_id}", content_id

    if key.startswith("images/") and len(parts) >= 7:
        # images/2026/03/07/{source}/{id}/{filename}
        #   idx:   0    1   2   3      4     5       6
        source = parts[-3]   # e.g. "abcnews"
        content_id = parts[-2]   # the folder that is the ID
        return f"hackcanada/news/{source}/{content_id}", content_id

    return None


def is_video(key: str) -> bool:
    return PurePosixPath(key).suffix.lower() in VIDEO_EXTENSIONS


def s3_public_url(bucket: str, region: str, key: str) -> str:
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def find_content_row(cur, s3_url: str, content_id: str) -> tuple | None:
    """Return (id,) from content_table matching by s3 URL first, then by id."""
    # Match by the S3 URL stored in image_url
    cur.execute(
        "SELECT id FROM content_table WHERE image_url = %s AND s3_url IS NULL LIMIT 1",
        (s3_url,),
    )
    row = cur.fetchone()
    if row:
        return row

    # Match by content_table.id directly (works when ID in S3 path == UUID in DB)
    cur.execute(
        "SELECT id FROM content_table WHERE id::text = %s AND s3_url IS NULL LIMIT 1",
        (content_id,),
    )
    return cur.fetchone()


def main() -> None:
    # Cloudinary
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
    )

    # S3
    bucket = os.environ["S3_BUCKET"]
    region = os.environ.get("AWS_REGION", "ca-central-1")
    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

    # Postgres
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.environ["PG_HOST"],
            port=int(os.environ.get("PG_PORT", "5432")),
            user=os.environ["PG_USER"],
            password=os.environ["PG_PASSWORD"],
            dbname=os.environ["PG_DB"],
        )
    cur = conn.cursor()

    # Ensure s3_url column exists
    cur.execute("ALTER TABLE content_table ADD COLUMN IF NOT EXISTS s3_url TEXT")
    conn.commit()
    log.info("s3_url column ensured")

    # Collect all S3 keys across the known prefixes
    all_keys: list[str] = []
    for prefix in SCAN_PREFIXES:
        log.info("Scanning s3://%s/%s ...", bucket, prefix)
        paginator = s3.get_paginator("list_objects_v2")
        count_before = len(all_keys)
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if is_real_file(key):
                    all_keys.append(key)
        log.info("  → found %d files under %s", len(all_keys) - count_before, prefix)

    log.info("Total: %d media files to process in s3://%s", len(all_keys), bucket)
    print()  # blank line before per-file output

    migrated = 0
    no_db_match = 0
    already_done = 0
    errors = 0

    eager = [{"width": 720, "height": 720, "crop": "fill", "gravity": "auto"}]

    total = len(all_keys)
    for i, key in enumerate(all_keys, start=1):
        classified = classify_key(key)
        if classified is None:
            log.warning("[SKIP] Unrecognised path structure: %s", key)
            continue

        public_id, content_id = classified
        original_s3_url = s3_public_url(bucket, region, key)

        log.info("--- [%d/%d] %s", i, total, key)

        try:
            # Check if already migrated (s3_url already set for this key)
            cur.execute(
                "SELECT id FROM content_table WHERE s3_url = %s LIMIT 1",
                (original_s3_url,),
            )
            if cur.fetchone():
                already_done += 1
                log.info("  [SKIP] Already migrated, skipping.")
                continue

            # Find matching content_table row
            db_row = find_content_row(cur, original_s3_url, content_id)
            if db_row is None:
                log.warning("  [NO DB MATCH] content_id='%s' not found in content_table", content_id)
                no_db_match += 1
                continue

            db_id = db_row[0]
            log.info("  Matched DB row  : %s", db_id)

            # Generate presigned URL for the private bucket
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=900,
            )
            log.info("  Presigned S3 URL: %s", presigned_url)

            # Upload to Cloudinary
            resource_type = "video" if is_video(key) else "image"
            log.info("  Uploading to Cloudinary as '%s' (type: %s)...", public_id, resource_type)
            result = cloudinary.uploader.upload(
                presigned_url,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=False,
                eager=eager,
            )

            if not result.get("public_id"):
                log.warning("[SKIP] Cloudinary returned no public_id for %s", key)
                continue

            cloudinary_url = result.get("secure_url", "")
            log.info("  Cloudinary URL : %s", cloudinary_url)
            log.info("  S3 source      : %s", original_s3_url)

            # Update DB: image_url → Cloudinary public_id, s3_url → original S3 URL
            cur.execute(
                "UPDATE content_table SET image_url = %s, s3_url = %s WHERE id = %s",
                (public_id, original_s3_url, db_id),
            )
            conn.commit()
            log.info("[OK] %s → %s (db id: %s)", key, public_id, db_id)
            migrated += 1

        except Exception as exc:
            conn.rollback()
            log.error("[ERROR] %s: %s", key, exc)
            errors += 1

    cur.close()
    conn.close()

    log.info(
        "Done. migrated=%d  no_db_match=%d  already_done=%d  errors=%d",
        migrated, no_db_match, already_done, errors,
    )


if __name__ == "__main__":
    main()
