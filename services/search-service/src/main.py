import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers import router as search_router
from src.core.qdrant_client import qdrant_client


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Search Service starting...")
    try:
        await qdrant_client.init_collection()
        logger.info("Qdrant collection 'notes' verified/created successfully")
    except Exception as e:
        logger.error("Qdrant init failed: %s", e)
        raise
    yield
    logger.info("Search Service shutting down...")


app = FastAPI(
    title="Vzametki Search Service",
    description="Векторный поиск (Qdrant)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search_router)