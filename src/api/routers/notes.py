from fastapi import APIRouter, Depends

from src.notes.service import NotesService
from src.notes.schemas import CreateNoteRequest
from src.api.dependency import get_db


router = APIRouter(prefix="/notes", tags=["notes"])

@router.post("/")
async def create_note(payload: CreateNoteRequest, session=Depends(get_db)) -> dict:
    service = NotesService(session)

    response = await service.create_note(
        payload=payload.model_dump()
    )

    return response

@router.get("/")
async def search_notes(text: str, session=Depends(get_db)):
    pass

@router.get("/all_my_notes")
async def get_notes(user_id: int, session=Depends(get_db)):
    pass

@router.get("/{note_id}")
async def get_note_by_id(note_id: str, session=Depends(get_db)):
    pass