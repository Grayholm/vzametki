import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.exceptions import AppError


logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: Any) -> JSONResponse:
    """Глобальный обработчик для кастомных ошибок приложения."""
    if isinstance(exc, AppError):
        logger.warning(
            "AppError: %s | status=%s | user_message=%s",
            exc.message,
            exc.status_code,
            exc.user_message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.user_message},
        )

    # Неизвестная ошибка — отдаём 500
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера."},
    )