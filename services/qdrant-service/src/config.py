import os
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODE: Literal["dev", "test"] = "dev"
    EXCHANGE_NAME: str
    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_API_KEY: str
    QDRANT_SCHEME: Literal["http", "https"] = "http"

    RABBITMQ_HOST: str
    RABBITMQ_PORT: int

    AI_SERVICE_URL: str

    LOG_LEVEL: str

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


settings = Settings() # type: ignore[call-arg]