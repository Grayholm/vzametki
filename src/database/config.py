import os
from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    explicit_env_file = os.getenv("ENV_FILE")
    if explicit_env_file:
        return explicit_env_file

    mode = os.getenv("MODE", "dev")
    env_file = Path(f".env.{mode}")

    if env_file.exists():
        return str(env_file)

    return ".env"


class Settings(BaseSettings):
    MODE: Literal["dev", "test", "prod"]
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

    TELEGRAM_BOT_TOKEN: str
    FASTAPI_URL: str

    model_config = SettingsConfigDict(
        env_file=get_env_file(), env_file_encoding="utf8", extra="ignore"
    )

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

settings = Settings()
