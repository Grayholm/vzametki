import logging

import httpx
from fastapi import APIRouter, HTTPException

from src.config import settings


logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic схемы для валидации входящих запросов
from pydantic import BaseModel


class ProcessMessageRequest(BaseModel):
    user_id: int
    text: str
    category: str | None = None


class NoteUpdateText(BaseModel):
    full_text: str



@router.post("/notes/process")
async def proxy_process_message(payload: ProcessMessageRequest):
    """POST /notes/process → notes-service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
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
    """POST /notes/classify → notes-service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
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
    """GET /notes/{user_id}/list → notes-service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{settings.service_notes_url}/notes/{user_id}/list",
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/notes/{user_id}/{note_id}")
async def proxy_get_note(user_id: int, note_id: int):
    """GET /notes/{user_id}/{note_id} → notes-service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{settings.service_notes_url}/notes/{user_id}/{note_id}",
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.put("/notes/{user_id}/{note_id}")
async def proxy_update_note(user_id: int, note_id: int, data: NoteUpdateText):
    """PUT /notes/{user_id}/{note_id} → notes-service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
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
    """DELETE /notes/{user_id}/{note_id} → notes-service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(
            f"{settings.service_notes_url}/notes/{user_id}/{note_id}",
        )
    if resp.is_error:
        logger.error("Notes service error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()