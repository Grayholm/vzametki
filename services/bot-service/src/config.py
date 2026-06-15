import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


class Settings(BaseSettings):
    MODE: Literal["dev", "test"] = "dev"
    TELEGRAM_BOT_TOKEN: str
    API_GATEWAY_URL: str

    # Redis (для rate limit)
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    BOT_RATE_LIMIT_MESSAGES: int
    BOT_RATE_LIMIT_SECONDS: int

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('MODE', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings() # type: ignore[call-arg]

if not settings.TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment")

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
