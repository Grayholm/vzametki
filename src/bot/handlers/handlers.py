import logging

import httpx

from src.database.config import settings
from src.exceptions import ApiClientError, AppError


logger = logging.getLogger(__name__)

CONFIRM_CATEGORIES = {"Note", "Idea", "Noise"}
PROCESS_TIMEOUT = 60.0


def _raise_api_error(response: httpx.Response, *, action: str) -> None:
    detail = "Ошибка сервера заметок."
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("detail"):
            detail = body["detail"]
    except Exception:
        pass

    logger.error(
        "API %s failed: status=%s detail=%s",
        action,
        response.status_code,
        detail,
    )
    raise ApiClientError(
        f"API {action} failed with status {response.status_code}",
        user_message=detail,
        status_code=response.status_code,
    )


async def _post_json(path: str, payload: dict, *, action: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.FASTAPI_URL}{path}",
                json=payload,
                timeout=PROCESS_TIMEOUT,
            )
    except httpx.TimeoutException as exc:
        logger.error("API %s timeout: %s", action, exc)
        raise ApiClientError(
            f"API {action} timeout",
            user_message="Сервер долго не отвечает. Попробуй позже.",
            status_code=504,
        ) from exc
    except httpx.RequestError as exc:
        logger.error("API %s connection error: %s", action, exc)
        raise ApiClientError(
            f"API {action} connection error: {exc}",
            user_message="Не удалось подключиться к API. Запущен ли uvicorn?",
            status_code=502,
        ) from exc

    if response.is_error:
        _raise_api_error(response, action=action)

    return response.json()


async def classify_message(user_id: int, text: str) -> str:
    data = await _post_json(
        "/notes/classify",
        {"user_id": user_id, "text": text},
        action="classify",
    )
    return data["category"]


async def process_message(
    user_id: int, text: str, category: str | None = None
) -> dict:
    payload: dict = {"user_id": user_id, "text": text}
    if category is not None:
        payload["category"] = category
    return await _post_json("/notes/process", payload, action="process")


def user_message_from_error(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.user_message
    return "Произошла непредвиденная ошибка. Попробуй позже."
