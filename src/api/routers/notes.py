from fastapi import APIRouter, Depends

from src.notes.service import NotesService
from src.notes.schemas import NoteUpdateText, ProcessMessageRequest
from src.api.dependency import get_notes_service


router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/classify")
async def classify_message(payload: ProcessMessageRequest, service: NotesService = Depends(get_notes_service)) -> dict:
    category, note_id = await service.classify_text(payload.text)
    result: dict[str, object] = {"category": category}
    if note_id is not None:
        result["note_id"] = note_id
    return result


@router.post("/process")
async def process_message(payload: ProcessMessageRequest, service: NotesService = Depends(get_notes_service)) -> dict:
    return await service.process_text(
        user_id=payload.user_id,
        full_text=payload.text,
        category=payload.category,
    )


@router.get("/{user_id}/list")
async def list_all_notes(user_id: int, service: NotesService = Depends(get_notes_service)) -> dict:
    notes = await service.list_all_notes(user_id)
    return notes


@router.get("/{user_id}/{note_id}")
async def get_note_by_id(user_id: int, note_id: int, service: NotesService = Depends(get_notes_service)) -> dict:
    note = await service.get_note_by_id(user_id, note_id)
    if note:
        return note
    return {
        "note": None,
        "action": "get_by_id",
        }


@router.put("/{user_id}/{note_id}")
async def update_note(
    user_id: int, note_id: int, data: NoteUpdateText, service: NotesService = Depends(get_notes_service)
) -> dict:
    await service.update_note(user_id, note_id, data.full_text)
    return {"action": "updated", "note_id": note_id}


@router.delete("/{user_id}/{note_id}")
async def delete_note(user_id: int, note_id: int, service: NotesService = Depends(get_notes_service)) -> dict:
    await service.delete_note(user_id, note_id)
    return {"action": "deleted", "note_id": note_id}
