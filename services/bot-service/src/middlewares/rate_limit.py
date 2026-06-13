import logging

from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.config import settings


logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        limit: int = settings.BOT_RATE_LIMIT_MESSAGES,
        window_seconds: int = settings.BOT_RATE_LIMIT_SECONDS,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis_client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
        )

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        key = f"rate_limit:bot:messages:{event.from_user.id}"

        try:
            current_count = await self.redis_client.incr(key)
            if current_count == 1:
                await self.redis_client.expire(key, self.window_seconds)
        except Exception as error:
            logger.warning("Rate limit check failed: %s", error)
            return await handler(event, data)

        if current_count > self.limit:
            await event.answer("Слишком часто. Подожди немного.")
            return None

        return await handler(event, data)