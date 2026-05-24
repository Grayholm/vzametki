import asyncio
import json
import logging

from src.database.embedding import EmbeddingManager
from src.ai.groq_client import GroqClient
from src.exceptions import AppError, NoteStorageError
from src.notes.repository import NotesRepository
from src.database.qdrant_client import qdrant_client
from src.database.redis_config import redis_manager
from src.notes.schemas import NoteSchema


logger = logging.getLogger(__name__)


class NotesService:
    def __init__(self, session):
        self.session = session
        self.redis_client = redis_manager
        self.repo = NotesRepository(session)
        self.groq_client = GroqClient()
        self.emb_client = EmbeddingManager()
        self.qdrant_client = qdrant_client

    async def classify_text(self, text: str) -> tuple[str, int | None]:
        result = await self.groq_client.classify_note_content(text)
        if isinstance(result, dict):
            category = result.get("category", "").strip().strip('"')
            note_id = result.get("note_id")
        else:
            category = str(result).strip().strip('"')
            note_id = None

        valid = {"Note", "Idea", "Noise", "Search", "ListAll", "GetById", "Trash"}
        if category in valid:
            return category, note_id
        return "Trash", None

    async def generate_note_metadata(
        self, full_text: str, category: str | None = None
    ) -> tuple[str, str]:
        response = await self.groq_client.generate_note_title_summary(
            full_text,
            category=category,
        )
        title = response.get("title", "")
        summary = response.get("summary", "")
        return title, summary

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

        note_id = await self.repo.create_note(note_data)

        try:
            vector = await asyncio.to_thread(self.emb_client.embed_text, full_text)
            await self.qdrant_client.insert_note_vector(
                note_id=note_id,
                vector=vector,
                payload=note_data_for_qdrant,
            )
        except AppError:
            raise
        except Exception as exc:
            logger.error(
                "Vector store failed after note %s saved to Postgres: %s",
                note_id,
                exc,
            )
            raise NoteStorageError(
                f"Note {note_id} saved to Postgres but vector insert failed: {exc}",
            ) from exc
        
        await self.session.commit()

        return {
            "note_id": note_id,
            "title": title,
            "summary": summary,
            "category": category,
        }

    async def search_notes(self, user_id: int, query: str | None, top_k: int = 5) -> dict:
        if query:
            vector = await asyncio.to_thread(self.emb_client.embed_text, query)
            results = await self.qdrant_client.search_similar_notes(
                user_id, vector, top_k=top_k
            )
            return {
                "query": query,
                "results": results,
            }
        else:
            results = await self.qdrant_client.search_similar_notes(
                user_id, top_k=top_k
            )
            return {
                "results": results,
            }

    async def list_all_notes(self, user_id: int, limit: int = 100) -> list[dict]:
        try:
            results = await self.qdrant_client.scroll_notes_by_user_id(
                user_id, limit=limit
            )
            return {
                "category": "ListAll",
                "action": "list_all",
                "notes": results,
            }
        except AppError:
            raise
        except Exception as exc:
            logger.error("Failed to list notes for user %s: %s", user_id, exc)
            return []

    async def get_note_by_id(self, user_id: int, note_id: int) -> dict | None:
        def get_note(note: dict):
            return {
                "category": "GetById",
                "action": "get_by_id",
                "note": note,
            }

        try:
            cached_note = await self.redis_client.get_value(note_id)
            if cached_note:
                note = json.loads(cached_note)
                return get_note(note)

            note = await self.repo.get_note_by_id(user_id, note_id)
            if note:
                note_schema = NoteSchema.model_validate(note)
                await self.redis_client.set_value(
                    note_id, note_schema.model_dump_json(), ttl=3600
                )

                logger.info(">>> %s", note_schema.model_dump())

                return get_note(note_schema.model_dump())
            return None
        except AppError:
            raise
        except Exception as exc:
            logger.warning("get_note_by_id failed for %s: %s", note_id, exc)
            return None

    async def process_text(
        self, user_id: int, full_text: str, category: str | None = None
    ) -> dict:
        if category is None:
            category, extracted_id = await self.classify_text(full_text)

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
