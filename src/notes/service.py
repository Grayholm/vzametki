from src.database.embedding import EmbeddingManager
from src.ai.groq_client import GroqClient
from src.notes.repository import NotesRepository
from src.database.qdrant_client import qdrant_client
from src.database.redis_config import redis_manager


class NotesService:
    def __init__(self, session):
        self.session = session
        self.redis_client = redis_manager
        self.repo = NotesRepository(session)
        self.groq_client = GroqClient()
        self.emb_client = EmbeddingManager()
        self.qdrant_client = qdrant_client

    async def generate_note_metadata(self, full_text: str) -> tuple[str, str]:
        try:
            response = await self.groq_client.generate_note_title_summary(full_text)
            title = response.get("title", "")
            summary = response.get("summary", "")
            return title, summary
        except Exception:
            return "", ""

    async def create_note(self, payload: dict) -> dict:
        full_text = payload.get("full_text", "")

        title, summary = await self.generate_note_metadata(full_text)

        note_data = {
            "user_id": payload.get("user_id"),
            "title": title,
            "summary": summary,
            "full_text": full_text
        }

        note_data_for_qdrant = {
            "user_id": payload.get("user_id"),
            "title": title,
            "summary": summary,
        }

        note_id = await self.repo.create_note(note_data)

        vector = self.emb_client.embed_text(full_text)
        await self.qdrant_client.insert_note_vector(
            note_id=note_id,
            vector=vector,
            payload=note_data_for_qdrant,
        )

        answer = {
            "note_id": note_id,
            "title": title,
            "summary": summary
        }
        return answer
    

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
