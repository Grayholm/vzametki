from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from src.database.redis_config import redis_manager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_manager.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis unavailable, continuing without cache: %s", e)

    yield

    try:
        await redis_manager.close()
    except Exception as e:
        logger.warning("Redis close failed: %s", e)

app = FastAPI(lifespan=lifespan)