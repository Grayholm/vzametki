import os
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODE: Literal["local", "dev", "test", "prod"]
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_SCHEME: Literal["http", "https"] = "http"

    TELEGRAM_BOT_TOKEN: str
    FASTAPI_URL: str
    BOT_RATE_LIMIT_MESSAGES: int = 5
    BOT_RATE_LIMIT_SECONDS: int = 10

    GROQ_API_KEY: str
    GROQ_NOTE_GENERATION_MODEL: str

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('MODE', 'local')}",
        env_file_encoding="utf8",
        extra="ignore",
    )

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def qdrant_url(self) -> str:
        return f"{self.QDRANT_SCHEME}://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

settings = Settings()
