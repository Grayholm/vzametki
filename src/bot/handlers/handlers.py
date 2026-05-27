import logging

import httpx

from src.api.dependency import http_client
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


async def _get_json(
    path: str,
    payload: dict | None = None,
    *,
    action: str,
) -> dict:

    try:
        response = await http_client.get(
            f"{settings.FASTAPI_URL}{path}",
            params=payload,
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
            user_message="Не удалось подключиться к API.",
            status_code=502,
        ) from exc

    if response.is_error:
        _raise_api_error(response, action=action)

    return response.json()


async def _post_json(
    path: str,
    payload: dict,
    *,
    action: str,
) -> dict:

    try:
        response = await http_client.post(
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


async def classify_message(user_id: int, text: str) -> dict:
    data = await _post_json(
        "/notes/classify",
        {"user_id": user_id, "text": text},
        action="classify",
    )
    return data


async def process_message(
    user_id: int, text: str, category: str | None = None, note_id: int | None = None
) -> dict:
    payload: dict = {"user_id": user_id, "text": text}
    if category is not None:
        payload["category"] = category
    if note_id is not None:
        payload["note_id"] = note_id

    match category:
        case "GetById":
            return await _get_json(f"/notes/{user_id}/{note_id}", action="process")
        case "ListAll":
            return await _get_json(f"/notes/{user_id}/list", action="process")
        case _:
            return await _post_json("/notes/process", payload=payload, action="process")


async def _put_json(
    path: str,
    payload: dict,
    *,
    action: str,
) -> dict:
    try:
        response = await http_client.put(
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


async def _delete_json(
    path: str,
    *,
    action: str,
) -> dict:
    try:
        response = await http_client.delete(
            f"{settings.FASTAPI_URL}{path}",
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


async def update_message(user_id: int, note_id: int, full_text: str) -> dict:
    return await _put_json(
        f"/notes/{user_id}/{note_id}",
        {"user_id": user_id, "note_id": note_id, "full_text": full_text},
        action="update",
    )


async def delete_message(user_id: int, note_id: int) -> dict:
    return await _delete_json(
        f"/notes/{user_id}/{note_id}",
        action="delete",
    )


def user_message_from_error(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.user_message
    return "Произошла непредвиденная ошибка. Попробуй позже."
