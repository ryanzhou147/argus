import asyncio
import logging
import json

from ..ingestion_service import run_acled_ingestion
from ..db import close_pool

logging.basicConfig(level=logging.INFO)

async def main():
    try:
        summary = await run_acled_ingestion()
        print(summary.model_dump_json(indent=2))
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
