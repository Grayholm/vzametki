import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from src.exceptions import AppError


logger = logging.getLogger(__name__)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    logger.warning("%s: %s", exc.__class__.__name__, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.user_message,
            "error": exc.__class__.__name__,
        },
    )


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Внутренняя ошибка сервера.",
            "error": "InternalServerError",
        },
    )
