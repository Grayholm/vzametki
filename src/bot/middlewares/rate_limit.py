import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from src.database.config import settings
from src.database.redis_config import redis_manager


logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        limit: int = settings.BOT_RATE_LIMIT_MESSAGES,
        window_seconds: int = settings.BOT_RATE_LIMIT_SECONDS,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        key = f"rate_limit:bot:messages:{event.from_user.id}"

        try:
            current_count = await redis_manager.redis_client.incr(key)
            if current_count == 1:
                await redis_manager.redis_client.expire(key, self.window_seconds)
        except Exception as error:
            logger.warning("Rate limit check failed: %s", error)
            return await handler(event, data)

        if current_count > self.limit:
            await event.answer("Слишком часто. Подожди немного.")
            return None

        return await handler(event, data)
