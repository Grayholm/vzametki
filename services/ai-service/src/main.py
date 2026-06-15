import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exception_handlers import app_error_handler
from src.api.routers import router as ai_router
from src.exceptions import AppError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Service starting...")
    yield
    logger.info("AI Service shutting down...")


app = FastAPI(
    title="Vzametki AI Service",
    description="Groq классификация + генерация метаданных + BGE эмбеддинги",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(ai_router)
