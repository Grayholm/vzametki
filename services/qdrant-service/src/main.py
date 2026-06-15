import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers import router as search_router
from src.core.qdrant_client import qdrant_client
from src.messaging.consumer import consumer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Qdrant Service starting...")
    try:
        await qdrant_client.init_collection()
        logger.info("Qdrant collection 'notes' verified/created successfully")
    except Exception as e:
        logger.error("Qdrant init failed: %s", e)
        raise
    try:
        await consumer.start()
        logger.info("RabbitMQ consumer started")
    except Exception as e:
        logger.warning("RabbitMQ unavailable, continuing without broker: %s", e)
    yield
    await consumer.close()
    logger.info("Qdrant Service shutting down...")


app = FastAPI(
    title="Vzametki Qdrant Service",
    description="Векторный поиск (Qdrant)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search_router)