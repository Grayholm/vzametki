import httpx

from fastapi import Depends

from src.database.db import async_session_maker
from src.notes.service import NotesService


async def get_db():
    async with async_session_maker() as session:
        yield session


async def get_notes_service(session=Depends(get_db)) -> NotesService:
    return NotesService(session=session)


http_client = httpx.AsyncClient()