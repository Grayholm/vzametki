import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODE: Literal["dev", "test"] = "dev"
    GROQ_API_KEY: str
    GROQ_NOTE_GENERATION_MODEL: str

    RABBITMQ_HOST: str
    RABBITMQ_PORT: int

    LOG_LEVEL: str

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('MODE', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings() # type: ignore[call-arg]