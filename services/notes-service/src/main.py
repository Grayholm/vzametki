import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exception_handlers import app_error_handler
from src.api.routers import router as notes_router
from src.exceptions import AppError
from src.infrastructure.redis import redis_manager
from src.messaging.producer import producer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Notes Service starting...")
    try:
        await redis_manager.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis unavailable, continuing without cache: %s", e)
    try:
        await producer.connect()
        logger.info("RabbitMQ connected")
    except Exception as e:
        logger.warning("RabbitMQ unavailable, continuing without broker: %s", e)
    yield
    await producer.close()
    try:
        await redis_manager.close()
    except Exception as e:
        logger.warning("Redis close failed: %s", e)
    logger.info("Notes Service shutting down...")


app = FastAPI(
    title="Vzametki Notes Service",
    description="CRUD для заметок (Postgres + Redis)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(notes_router)
