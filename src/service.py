from src.repository import NotesRepository
from src.database.redis_config import redis_manager


class NotesService:
    def __init__(self, session):
        self.session = session
        self.redis_client = redis_manager
        self.repo = NotesRepository(session)

    async def generate_note_metadata(self, full_text: str) -> tuple[str, str]:
        return "", ""

    async def create_note(self, payload: dict):
        full_text = payload.get("full_text", "")

        title, summary = await self.generate_note_metadata(full_text)

        note_data = {
            "user_id": payload.get("user_id"),
            "title": title,
            "summary": summary,
            "full_text": full_text
        }
        try:
            note_id = await self.repo.create_note(note_data)
            return note_id
        except Exception as e:
            raise e
    

    async def search_notes(self, query: str):
        pass


    async def get_note_by_id(self, note_id: str):
        cached_note = await self.redis_client.get_value(note_id)
        if cached_note:
            return cached_note
        
        note = await self.repo.get_note_by_id(note_id)
        if note:
            await self.redis_client.set_value(note_id, note)
        return note