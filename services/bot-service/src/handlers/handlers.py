import logging

import httpx

from src.config import settings


logger = logging.getLogger(__name__)

CONFIRM_CATEGORIES = {"Note", "Idea", "Noise"}
PROCESS_TIMEOUT = 60.0

API_BASE_URL = settings.API_GATEWAY_URL


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
    raise Exception(detail)


async def _post_json(
    path: str,
    payload: dict,
    *,
    action: str,
) -> dict:
    async with httpx.AsyncClient(timeout=PROCESS_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}{path}",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            logger.error("API %s timeout: %s", action, exc)
            raise Exception("Сервер долго не отвечает. Попробуй позже.") from exc
        except httpx.RequestError as exc:
            logger.error("API %s connection error: %s", action, exc)
            raise Exception("Не удалось подключиться к API.") from exc

        if response.is_error:
            _raise_api_error(response, action=action)

        return response.json()


async def _get_json(
    path: str,
    *,
    action: str,
) -> dict:
    async with httpx.AsyncClient(timeout=PROCESS_TIMEOUT) as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}{path}",
            )
        except httpx.TimeoutException as exc:
            logger.error("API %s timeout: %s", action, exc)
            raise Exception("Сервер долго не отвечает. Попробуй позже.") from exc
        except httpx.RequestError as exc:
            logger.error("API %s connection error: %s", action, exc)
            raise Exception("Не удалось подключиться к API.") from exc

        if response.is_error:
            _raise_api_error(response, action=action)

        return response.json()


async def _put_json(
    path: str,
    payload: dict,
    *,
    action: str,
) -> dict:
    async with httpx.AsyncClient(timeout=PROCESS_TIMEOUT) as client:
        try:
            response = await client.put(
                f"{API_BASE_URL}{path}",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            logger.error("API %s timeout: %s", action, exc)
            raise Exception("Сервер долго не отвечает. Попробуй позже.") from exc
        except httpx.RequestError as exc:
            logger.error("API %s connection error: %s", action, exc)
            raise Exception("Не удалось подключиться к API.") from exc

        if response.is_error:
            _raise_api_error(response, action=action)

        return response.json()


async def _delete_json(
    path: str,
    *,
    action: str,
) -> dict:
    async with httpx.AsyncClient(timeout=PROCESS_TIMEOUT) as client:
        try:
            response = await client.delete(
                f"{API_BASE_URL}{path}",
            )
        except httpx.TimeoutException as exc:
            logger.error("API %s timeout: %s", action, exc)
            raise Exception("Сервер долго не отвечает. Попробуй позже.") from exc
        except httpx.RequestError as exc:
            logger.error("API %s connection error: %s", action, exc)
            raise Exception("Не удалось подключиться к API.") from exc

        if response.is_error:
            _raise_api_error(response, action=action)

        return response.json()


async def classify_message(user_id: int, text: str) -> dict:
    return await _post_json(
        "/notes/classify",
        {"user_id": user_id, "text": text},
        action="classify",
    )


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


async def update_message(user_id: int, note_id: int, full_text: str) -> dict:
    return await _put_json(
        f"/notes/{user_id}/{note_id}",
        {"full_text": full_text},
        action="update",
    )


async def delete_message(user_id: int, note_id: int) -> dict:
    return await _delete_json(
        f"/notes/{user_id}/{note_id}",
        action="delete",
    )


def user_message_from_error(exc: Exception) -> str:
    return str(exc)