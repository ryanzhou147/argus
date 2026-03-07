import asyncio
import logging
from datetime import datetime, timezone

import asyncpg

from .config import get_settings
from .openai_embedding_client import generate_embedding
from .embedding_repository import (
    create_hnsw_index,
    fetch_batch,
    update_embedding,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


def _build_text(title: str | None, body: str | None) -> str | None:
    """Construct input text from title and body. Returns None if both are empty."""
    t = (title or "").strip()
    b = (body or "").strip()
    if t and b:
        return t + "\n\n" + b
    if t:
        return t
    if b:
        return b
    return None


async def run_backfill() -> dict:
    settings = get_settings()
    started_at = datetime.now(timezone.utc)

    fetched = 0
    embedded = 0
    overwritten = 0
    empty_text_skipped = 0
    failed_rows = 0
    index_created = False
    status = "success"
    offset = 0

    pool = None
    try:
        pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=5)

        while True:
            async with pool.acquire() as conn:
                batch = await fetch_batch(conn, BATCH_SIZE, offset)

            if not batch:
                break

            fetched += len(batch)
            offset += len(batch)

            async with pool.acquire() as conn:
                async with conn.transaction():
                    for row in batch:
                        row_id = row["id"]
                        text = _build_text(row["title"], row["body"])

                        if text is None:
                            logger.info(f"Skipping row {row_id}: empty text")
                            empty_text_skipped += 1
                            continue

                        try:
                            embedding = generate_embedding(text)
                            if embedding is None:
                                raise RuntimeError("Embedding client returned None")
                            await update_embedding(conn, row_id, embedding)
                            embedded += 1
                            overwritten += 1
                        except Exception as e:
                            logger.error(f"Failed to embed row {row_id}: {e}")
                            failed_rows += 1

        # Attempt HNSW index creation
        async with pool.acquire() as conn:
            index_created = await create_hnsw_index(conn)

    except Exception as e:
        logger.error(f"Backfill run aborted: {e}")
        status = "failure"
    finally:
        if pool is not None:
            await pool.close()

    if status != "failure":
        status = "partial_success" if failed_rows > 0 else "success"

    finished_at = datetime.now(timezone.utc)

    return {
        "target": "content_table",
        "provider": "openai",
        "model": settings.openai_embedding_model,
        "dimensions": 1536,
        "fetched": fetched,
        "embedded": embedded,
        "overwritten": overwritten,
        "empty_text_skipped": empty_text_skipped,
        "failed_rows": failed_rows,
        "index_created": index_created,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "status": status,
    }
