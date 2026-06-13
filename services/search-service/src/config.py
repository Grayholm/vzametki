import os
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODE: Literal["dev", "test"] = "dev"
    QDRANT_HOST: Optional[str] = None
    QDRANT_PORT: Optional[int] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_SCHEME: Literal["http", "https"] = "http"

    RABBITMQ_HOST: Optional[str] = None
    RABBITMQ_PORT: Optional[int] = None

    AI_SERVICE_URL: Optional[str] = None

    LOG_LEVEL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=f".env.{os.getenv('MODE', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def qdrant_url(self) -> str:
        if not self.QDRANT_HOST or self.QDRANT_PORT is None:
            raise ValueError("QDRANT_HOST and QDRANT_PORT must be set")
        return f"{self.QDRANT_SCHEME}://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


settings = Settings()