import os
from typing import Optional, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


class Settings(BaseSettings):
    MODE: Literal["dev", "test"] = "dev"
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    API_GATEWAY_URL: Optional[str] = None

    # Redis (для rate limit)
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_DB: Optional[int] = None

    BOT_RATE_LIMIT_MESSAGES: Optional[int] = None
    BOT_RATE_LIMIT_SECONDS: Optional[int] = None

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('MODE', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

if not settings.TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment")

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
