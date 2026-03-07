import asyncpg
import logging
from typing import Dict, Any, Optional
import json

from .models import NormalizedRecord

logger = logging.getLogger(__name__)

async def ensure_sources(pool: asyncpg.Pool) -> Dict[str, int]:
    """
    Ensures ACLED source exists.
    Returns a dict mapping source names to their IDs.
    """
    sources_to_ensure = [
        ("ACLED", "api", "https://acleddata.com/api/", 0.90)
    ]
    
    source_ids = {}
    async with pool.acquire() as conn:
        for name, src_type, url, trust in sources_to_ensure:
            # Check if exists
            row = await conn.fetchrow("SELECT id FROM sources WHERE name = $1", name)
            if row:
                source_ids[name] = row["id"]
            else:
                # Insert
                new_id = await conn.fetchval("""
                    INSERT INTO sources (name, type, base_url, trust_score) 
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, name, src_type, url, trust)
                source_ids[name] = new_id
                logger.info(f"Inserted new source: {name} (ID: {new_id})")
                
    return source_ids

async def insert_content(pool: asyncpg.Pool, record: NormalizedRecord, source_id: int):
    """
    Inserts a normalized record into the content_table.
    """
    async with pool.acquire() as conn:
        # Pydantic dict handles enums properly
        meta_json = json.dumps(record.raw_metadata_json)
        
        await conn.execute("""
            INSERT INTO content_table 
            (source_id, title, body, url, published_at, latitude, longitude, event_type, raw_metadata_json, created_at)
            VALUES 
            ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, NOW())
        """, 
            source_id,
            record.title,
            record.body,
            record.url,
            record.published_at,
            record.latitude,
            record.longitude,
            record.event_type.value,
            meta_json
        )
