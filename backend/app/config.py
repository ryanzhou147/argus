import os
from dotenv import load_dotenv

# Load from .env file if it exists
load_dotenv()

GEMINI_API_KEY: str | None = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash") # Use flash model

# Agent defaults
AGENT_CONFIDENCE_THRESHOLD: float = 0.5
AGENT_MIN_INTERNAL_RESULTS: int = 2
AGENT_MAX_RETRIEVAL_LIMIT: int = 10
AGENT_WEB_FALLBACK_LIMIT: int = 3
