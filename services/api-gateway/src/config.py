import os
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODE: Literal["dev", "test"] = "dev"
    # URL-ы внутренних сервисов
    SERVICE_NOTES_URL: str
    SERVICE_AI_URL: str
    QDRANT_SERVICE_URL: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    LOG_LEVEL: str

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('MODE', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings() # type: ignore[call-arg]