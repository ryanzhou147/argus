import asyncio
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from .embedding_backfill_service import run_backfill


def main():
    summary = asyncio.run(run_backfill())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
