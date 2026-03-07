import asyncpg
import logging
from .config import get_settings

logger = logging.getLogger(__name__)
_pool = None

async def get_pool():
    """Lazily initialize and return the asyncpg connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        try:
            logger.info("Initializing DB connection pool...")
            _pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=2,
                max_size=10
            )
        except Exception as e:
            logger.error(f"Failed to create DB pool: {e}")
            raise
    return _pool

async def close_pool():
    """Explicitly close the connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing DB connection pool...")
        await _pool.close()
        _pool = None
