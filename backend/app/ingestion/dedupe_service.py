import asyncpg

async def is_duplicate(pool: asyncpg.Pool, source_id: int, native_id: str, url: str) -> bool:
    """
    Checks if a record is a duplicate.
    Order of checks:
    1. By source_id + source_native_id (extracted from raw_metadata_json)
    2. By source_id + url
    """
    async with pool.acquire() as conn:
        # Check 1: By source_native_id
        if native_id:
            exists_by_id = await conn.fetchval("""
                SELECT 1 FROM content_table 
                WHERE source_id = $1 
                  AND raw_metadata_json->>'source_native_id' = $2
                LIMIT 1
            """, source_id, native_id)
            if exists_by_id:
                return True

        # Check 2: By URL
        if url:
            exists_by_url = await conn.fetchval("""
                SELECT 1 FROM content_table 
                WHERE source_id = $1 
                  AND url = $2
                LIMIT 1
            """, source_id, url)
            if exists_by_url:
                return True
                
    return False
