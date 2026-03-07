from pydantic_settings import BaseSettings


class EmbeddingSettings(BaseSettings):
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    database_url: str

    class Config:
        env_file = ".env"
        extra = "ignore"


_settings = None


def get_settings() -> EmbeddingSettings:
    global _settings
    if _settings is None:
        _settings = EmbeddingSettings()
    return _settings
