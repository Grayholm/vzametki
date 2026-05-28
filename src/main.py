import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from src.api.exception_handlers import app_error_handler, unhandled_error_handler
from src.database.qdrant_client import qdrant_client
from src.database.redis_config import redis_manager
from src.api.dependency import http_client
from src.exceptions import AppError

from src.api.routers.notes import router as notes_router


os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    handlers=[
        RotatingFileHandler(
            "logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_manager.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis unavailable, continuing without cache: %s", e)

    try:
        await qdrant_client.init_collection()
        logger.info("Qdrant collection 'notes' verified/created successfully")
    except Exception as e:
        logger.error("Qdrant init failed: %s", e)
        raise

    yield

    try:
        await redis_manager.close()
    except Exception as e:
        logger.warning("Redis close failed: %s", e)

    await http_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(notes_router)
