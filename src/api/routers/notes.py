from fastapi import APIRouter, Depends, HTTPException

from src.notes.service import NotesService
from src.notes.schemas import CreateNoteRequest, ProcessMessageRequest
from src.api.dependency import get_db


router = APIRouter(prefix="/notes", tags=["notes"])

@router.post("/classify")
async def classify_message(payload: ProcessMessageRequest, session=Depends(get_db)) -> dict:
    service = NotesService(session)
    category = await service.classify_text(payload.text)
    return {"category": category}

@router.post("/process")
async def process_message(payload: ProcessMessageRequest, session=Depends(get_db)) -> dict:
    service = NotesService(session)
    return await service.process_text(
        user_id=payload.user_id,
        full_text=payload.text,
        category=payload.category,
    )