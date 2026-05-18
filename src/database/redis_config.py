import redis.asyncio as redis

from src.database.config import settings


class RedisManager:
    def __init__(self, host, port, db):
        self.redis_client = redis.Redis(
            host=host, port=port, db=db, decode_responses=True
        )

    async def ping(self):
        return await self.redis_client.ping()

    async def set_value(self, key: str, value: str, ttl: int = 300):
        await self.redis_client.set(key, value, ex=ttl)

    async def get_value(self, key):
        return await self.redis_client.get(key)

    async def delete_value(self, key):
        await self.redis_client.delete(key)

    async def close(self):
        await self.redis_client.close()


redis_manager = RedisManager(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)