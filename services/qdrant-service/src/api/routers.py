import asyncio
import logging

import httpx
from fastapi import APIRouter

from pydantic import BaseModel

from src.config import settings
from src.core.qdrant_client import qdrant_client


logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class InsertVectorRequest(BaseModel):
    note_id: int
    user_id: int
    text: str
    title: str
    summary: str
    category: str | None = None


class SearchRequest(BaseModel):
    user_id: int
    query: str


@router.get("/{user_id}/list")
async def list_notes(user_id: int) -> dict:
    """Список всех заметок пользователя (scroll из Qdrant)."""
    try:
        results = await qdrant_client.scroll_notes_by_user_id(user_id)
        return {"notes": results}
    except Exception as exc:
        logger.error("Failed to list notes for user %s: %s", user_id, exc)
        return {"notes": []}


@router.post("/search")
async def search_notes(payload: SearchRequest) -> dict:
    """Поиск заметок по смыслу (сначала эмбеддинг через ai-service, потом Qdrant)."""
    try:
        # 1. Получить эмбеддинг от ai-service
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}/embed",
                json={"text": payload.query},
            )
        resp.raise_for_status()
        vector = resp.json()["vector"]

        # 2. Поиск в Qdrant
        results = await qdrant_client.search_similar_notes(
            payload.user_id, vector, top_k=5
        )
        return {"query": payload.query, "results": results}
    except Exception as exc:
        logger.error("Search failed for user %s: %s", payload.user_id, exc)
        return {"query": payload.query, "results": []}


@router.post("/insert")
async def insert_note(payload: InsertVectorRequest) -> dict:
    """Вставка/обновление вектора заметки (сначала эмбеддинг, потом Qdrant)."""
    try:
        # 1. Получить эмбеддинг от ai-service
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}/embed",
                json={"text": payload.text},
            )
        resp.raise_for_status()
        vector = resp.json()["vector"]

        # 2. Сохранить в Qdrant
        await qdrant_client.insert_note_vector(
            note_id=payload.note_id,
            vector=vector,
            payload={
                "user_id": payload.user_id,
                "title": payload.title,
                "summary": payload.summary,
                "category": payload.category or "",
            },
        )
        return {"status": "inserted", "note_id": payload.note_id}
    except Exception as exc:
        logger.error("Insert failed for note %s: %s", payload.note_id, exc)
        return {"status": "error", "note_id": payload.note_id, "error": str(exc)}


@router.delete("/{note_id}")
async def delete_note(note_id: int) -> dict:
    """Удаление вектора заметки из Qdrant."""
    try:
        await qdrant_client.delete_note_vector(note_id)
        return {"status": "deleted", "note_id": note_id}
    except Exception as exc:
        logger.error("Delete failed for note %s: %s", note_id, exc)
        return {"status": "error", "note_id": note_id, "error": str(exc)}


@router.post("/init")
async def init_collection() -> dict:
    """Принудительная инициализация коллекции в Qdrant."""
    await qdrant_client.init_collection()
    return {"status": "ok", "collection": "notes"}