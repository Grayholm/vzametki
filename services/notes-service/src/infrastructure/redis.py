import logging

import redis.asyncio as aioredis

from src.infrastructure.config import settings


logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self) -> None:
        self.redis_client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    async def ping(self) -> bool:
        return await self.redis_client.ping()

    async def set_value(self, key: str | int, value: str, ttl: int = 300) -> None:
        await self.redis_client.set(str(key), value, ex=ttl)

    async def get_value(self, key: str | int) -> str | None:
        return await self.redis_client.get(str(key))

    async def delete_value(self, key: str | int) -> None:
        await self.redis_client.delete(str(key))

    async def close(self) -> None:
        await self.redis_client.close()


redis_manager = RedisManager()