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

    async def classify_text(self, text: str) -> str:
        category = await self.groq_client.classify_note_content(text)
        normalized = category.strip().strip('"')
        if normalized not in {"Note", "Idea", "Noise", "Search"}:
            return "Trash"
        return normalized

    async def generate_note_metadata(self, full_text: str, category: str | None = None) -> tuple[str, str]:
        try:
            response = await self.groq_client.generate_note_title_summary(
                full_text,
                category=category,
            )
            title = response.get("title", "")
            summary = response.get("summary", "")
            return title, summary
        except Exception as e:
            print(f"Ошибка при работе с Groq: {e}")
            return "Ошибка генерации", "Не удалось создать конспект"

    async def create_note(self, payload: dict) -> dict:
        full_text = payload.get("full_text", "")
        category = payload.get("category")

        title, summary = await self.generate_note_metadata(full_text, category=category)

        note_data = {
            "user_id": payload.get("user_id"),
            "title": title,
            "summary": summary,
            "full_text": full_text,
        }

        note_data_for_qdrant = {
            "user_id": payload.get("user_id"),
            "title": title,
            "summary": summary,
        }
        if category:
            note_data_for_qdrant["category"] = category

        try:
            note_id = await self.repo.create_note(note_data)
            vector = self.emb_client.embed_text(full_text)
            print(vector)
            await self.qdrant_client.insert_note_vector(
                note_id=note_id,
                vector=vector,
                payload=note_data_for_qdrant,
            )
        except Exception as e:
            print(f"Ошибка при сохранении заметки: {e}")
            raise e

        answer = {
            "note_id": note_id,
            "title": title,
            "summary": summary,
            "category": category,
        }
        return answer
    

    async def search_notes(self, user_id: int, query: str, top_k: int = 5) -> dict:
        vector = self.emb_client.embed_text(query)
        results = await self.qdrant_client.search_similar_notes(user_id, vector, top_k=top_k)
        return {
            "query": query,
            "results": results,
        }

    async def get_note_by_id(self, note_id: str):
        cached_note = await self.redis_client.get_value(note_id)
        if cached_note:
            return cached_note
        
        note = await self.repo.get_note_by_id(note_id)
        if note:
            await self.redis_client.set_value(note_id, note)
        return note


    async def process_text(self, user_id: int, full_text: str) -> dict:
        category = await self.classify_text(full_text)

        if category in {"Note", "Idea", "Noise"}:
            note = await self.create_note(
                {"user_id": user_id, "full_text": full_text, "category": category}
            )
            return {
                "category": category,
                "action": "created_note",
                "note": note,
            }

        if category == "Search":
            search = await self.search_notes(user_id, full_text)
            return {
                "category": category,
                "action": "search",
                "search": search,
            }

        return {
            "category": category,
            "action": "trash",
            "message": "Сообщение не похоже на заметку или запрос поиска.",
        }