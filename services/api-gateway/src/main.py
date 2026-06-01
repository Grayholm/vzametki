import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.routers.proxy import router as proxy_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Gateway starting...")
    yield
    logger.info("API Gateway shutting down...")


app = FastAPI(
    title="Vzametki API Gateway",
    description="Единая точка входа для всех микросервисов",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(proxy_router, prefix="")