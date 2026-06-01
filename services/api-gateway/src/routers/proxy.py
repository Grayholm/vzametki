import logging

import httpx
from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Схемы запросов (повторяем те, что есть в notes-service и ai-service)
# Чтобы Gateway знал, какие данные принимать от клиента
from pydantic import BaseModel


class ProcessMessageRequest(BaseModel):
    user_id: int
    text: str
    category: str | None = None


class NoteUpdateText(BaseModel):
    full_text: str


async def get_http_client() -> AsyncClient:
    """Создаёт HTTP-клиент для запросов к внутренним сервисам."""
    return httpx.AsyncClient(timeout=30.0)


# === Прокси к Notes Service ===

@router.post("/notes/process")
async def proxy_process_message(payload: ProcessMessageRequest):
    """Прокси: POST /notes/process → notes-service"""
    async with await get_http_client() as client:
        resp = await client.post(
            f"{settings.service_notes_url}/notes/process",
            json=payload.model_dump(),
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/notes/classify")
async def proxy_classify_message(payload: ProcessMessageRequest):
    """Прокси: POST /notes/classify → notes-service"""
    async with await get_http_client() as client:
        resp = await client.post(
            f"{settings.service_notes_url}/notes/classify",
            json=payload.model_dump(),
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/notes/{user_id}/list")
async def proxy_list_notes(user_id: int):
    """Прокси: GET /notes/{user_id}/list → notes-service"""
    async with await get_http_client() as client:
        resp = await client.get(
            f"{settings.service_notes_url}/notes/{user_id}/list",
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/notes/{user_id}/{note_id}")
async def proxy_get_note(user_id: int, note_id: int):
    """Прокси: GET /notes/{user_id}/{note_id} → notes-service"""
    async with await get_http_client() as client:
        resp = await client.get(
            f"{settings.service_notes_url}/notes/{user_id}/{note_id}",
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.put("/notes/{user_id}/{note_id}")
async def proxy_update_note(user_id: int, note_id: int, data: NoteUpdateText):
    """Прокси: PUT /notes/{user_id}/{note_id} → notes-service"""
    async with await get_http_client() as client:
        resp = await client.put(
            f"{settings.service_notes_url}/notes/{user_id}/{note_id}",
            json=data.model_dump(),
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.delete("/notes/{user_id}/{note_id}")
async def proxy_delete_note(user_id: int, note_id: int):
    """Прокси: DELETE /notes/{user_id}/{note_id} → notes-service"""
    async with await get_http_client() as client:
        resp = await client.delete(
            f"{settings.service_notes_url}/notes/{user_id}/{note_id}",
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# === Прокси к AI Service ===

@router.post("/ai/classify")
async def proxy_ai_classify(payload: ProcessMessageRequest):
    """Прокси: POST /ai/classify → ai-service"""
    async with await get_http_client() as client:
        resp = await client.post(
            f"{settings.service_ai_url}/classify",
            json={"text": payload.text},
        )
    if resp.is_error:
        logger.error("AI service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/ai/generate-metadata")
async def proxy_ai_generate_metadata(payload: ProcessMessageRequest):
    """Прокси: POST /ai/generate-metadata → ai-service"""
    async with await get_http_client() as client:
        resp = await client.post(
            f"{settings.service_ai_url}/generate-metadata",
            json={"text": payload.text, "category": payload.category},
        )
    if resp.is_error:
        logger.error("AI service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/ai/embed")
async def proxy_ai_embed(payload: ProcessMessageRequest):
    """Прокси: POST /ai/embed → ai-service"""
    async with await get_http_client() as client:
        resp = await client.post(
            f"{settings.service_ai_url}/embed",
            json={"text": payload.text},
        )
    if resp.is_error:
        logger.error("AI service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# === Прокси к Search Service ===

@router.post("/search/query")
async def proxy_search(payload: ProcessMessageRequest):
    """Прокси: POST /search/query → search-service"""
    async with await get_http_client() as client:
        resp = await client.post(
            f"{settings.service_search_url}/search",
            json={"user_id": payload.user_id, "query": payload.text},
        )
    if resp.is_error:
        logger.error("Search service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/search/{user_id}/list")
async def proxy_search_list(user_id: int):
    """Прокси: GET /search/{user_id}/list → search-service"""
    async with await get_http_client() as client:
        resp = await client.get(
            f"{settings.service_search_url}/{user_id}/list",
        )
    if resp.is_error:
        logger.error("Search service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()