from pydantic_settings import BaseSettings

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    api_gateway_url: str = "http://localhost:8080"

    # Redis (для rate limit)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    bot_rate_limit_messages: int = 10
    bot_rate_limit_seconds: int = 10

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher(storage=MemoryStorage())