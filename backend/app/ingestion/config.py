import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    acled_api_token: str
    ingestion_lookback_days: int = 14

    class Config:
        env_file = ".env"
        extra = "ignore"

_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
