import logging
from typing import Optional
import openai
from .config import get_settings

logger = logging.getLogger(__name__)


def generate_embedding(text: str) -> Optional[list[float]]:
    """Call OpenAI embeddings API and return a list of floats, or None on failure."""
    settings = get_settings()
    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding API error: {e}")
        return None
