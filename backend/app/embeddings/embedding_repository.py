import logging
from typing import Optional
import asyncpg

logger = logging.getLogger(__name__)


async def fetch_batch(
    conn: asyncpg.Connection,
    batch_size: int,
    exclude_ids: list[str] | None = None,
) -> list[asyncpg.Record]:
    """Fetch a batch of unembedded content_table rows, excluding specified IDs."""
    if exclude_ids:
        return await conn.fetch(
            "SELECT id, title, body FROM content_table WHERE embedding IS NULL AND id != ALL($2::uuid[]) LIMIT $1",
            batch_size,
            exclude_ids,
        )
    return await conn.fetch(
        "SELECT id, title, body FROM content_table WHERE embedding IS NULL LIMIT $1",
        batch_size,
    )


async def update_embedding(conn: asyncpg.Connection, row_id: str, embedding: list[float]) -> None:
    """Write an embedding vector to a single row by id."""
    await conn.execute(
        "UPDATE content_table SET embedding = $2::vector WHERE id = $1",
        row_id,
        str(embedding),
    )


async def hnsw_index_exists(conn: asyncpg.Connection) -> bool:
    """Check if an HNSW cosine index on content_table.embedding already exists."""
    result = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'content_table'
              AND indexdef ILIKE '%hnsw%'
              AND indexdef ILIKE '%embedding%'
        )
        """
    )
    return bool(result)


async def create_hnsw_index(conn: asyncpg.Connection) -> bool:
    """Create an HNSW cosine index on content_table.embedding if pgvector is available and the index doesn't exist.

    Returns True if the index was created, False otherwise.
    """
    try:
        # Check pgvector extension is available
        pgvector_available = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if not pgvector_available:
            logger.warning("pgvector extension not available; skipping HNSW index creation")
            return False

        if await hnsw_index_exists(conn):
            logger.info("HNSW index already exists; skipping creation")
            return False

        await conn.execute(
            "CREATE INDEX idx_content_table_embedding_hnsw ON content_table USING hnsw (embedding vector_cosine_ops)"
        )
        logger.info("HNSW cosine index created on content_table.embedding")
        return True
    except Exception as e:
        logger.error(f"Failed to create HNSW index: {e}")
        return False
