import json
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import NotesRepository
from src.core.schemas import NoteSchema
from src.exceptions import NoteStorageError
from src.infrastructure.config import settings
from src.infrastructure.redis import redis_manager


logger = logging.getLogger(__name__)


class NotesService:
    def __init__(
        self,
        session: AsyncSession,
        repo: NotesRepository | None = None,
    ) -> None:
        self.session = session
        self.repo = repo or NotesRepository(session)

    async def _call_ai(self, path: str, payload: dict) -> dict:
        """HTTP-вызов к ai-service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}{path}",
                json=payload,
            )
        resp.raise_for_status()
        return resp.json()

    async def _call_search(self, method: str, path: str, payload: dict | None = None) -> dict:
        """HTTP-вызов к search-service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "POST":
                resp = await client.post(f"{settings.SEARCH_SERVICE_URL}{path}", json=payload or {})
            elif method == "DELETE":
                resp = await client.delete(f"{settings.SEARCH_SERVICE_URL}{path}")
            else:
                resp = await client.get(f"{settings.SEARCH_SERVICE_URL}{path}")
        resp.raise_for_status()
        return resp.json()

    async def classify_text(self, text: str) -> tuple[str, int | None]:
        """Классификация через ai-service."""
        result = await self._call_ai("/classify", {"text": text})
        category = result.get("category", "Trash")
        note_id = result.get("note_id")
        return category, note_id

    async def generate_note_metadata(
        self, full_text: str, category: str | None = None
    ) -> tuple[str, str]:
        """Генерация заголовка и summary через ai-service."""
        result = await self._call_ai(
            "/generate-metadata",
            {"text": full_text, "category": category},
        )
        title = result.get("title", "")
        summary = result.get("summary", "")
        return title, summary

    async def create_note(self, payload: dict) -> dict:
        """Создать заметку в Postgres + отправить вектор в search-service."""
        full_text = payload.get("full_text", "")
        category = payload.get("category")

        title, summary = await self.generate_note_metadata(full_text, category=category)

        note_data = {
            "user_id": payload.get("user_id"),
            "title": title,
            "summary": summary,
            "full_text": full_text,
        }

        note_id = await self.repo.create_note(note_data)

        # Отправляем данные в search-service для векторизации и сохранения в Qdrant
        try:
            await self._call_search(
                "POST",
                "/insert",
                {
                    "note_id": note_id,
                    "user_id": payload.get("user_id"),
                    "text": full_text,
                    "title": title,
                    "summary": summary,
                    "category": category,
                },
            )
        except Exception as exc:
            logger.error(
                "Search service failed after note %s saved: %s",
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

    async def get_note_by_id(self, user_id: int, note_id: int) -> dict | None:
        """Получить заметку по ID (с Redis-кэшем)."""
        def _format_note(note: dict) -> dict:
            return {
                "category": "GetById",
                "action": "get_by_id",
                "note": note,
            }

        try:
            cached = await redis_manager.get_value(note_id)
            if cached:
                note = json.loads(cached)
                note_schema = NoteSchema.model_validate(note)
                return _format_note(note_schema.model_dump())

            note = await self.repo.get_note_by_id(user_id, note_id)
            if note:
                note_schema = NoteSchema.model_validate(note)
                await redis_manager.set_value(
                    note_id, note_schema.model_dump_json(), ttl=300
                )
                return _format_note(note_schema.model_dump())
            return None
        except Exception as exc:
            logger.warning("get_note_by_id failed for %s: %s", note_id, exc)
            return None

    async def list_all_notes(self, user_id: int) -> dict:
        """Список заметок — прокси к search-service."""
        try:
            result = await self._call_search("GET", f"/{user_id}/list")
            return {
                "category": "ListAll",
                "action": "list_all",
                "notes": result.get("notes", []),
            }
        except Exception as exc:
            logger.error("Failed to list notes for user %s: %s", user_id, exc)
            return {
                "category": "ListAll",
                "action": "list_all",
                "notes": [],
            }

    async def search_notes(self, user_id: int, query: str) -> dict:
        """Поиск заметок — прокси к search-service."""
        try:
            result = await self._call_search(
                "POST", "/search",
                {"user_id": user_id, "query": query},
            )
            return {
                "query": query,
                "results": result.get("results", []),
            }
        except Exception as exc:
            logger.error("Search failed for user %s: %s", user_id, exc)
            return {"query": query, "results": []}

    async def update_note(self, user_id: int, note_id: int, full_text: str) -> None:
        """Обновить заметку."""
        note = await self.repo.get_note_by_id(user_id, note_id)
        if note is None:
            raise NoteStorageError(f"Note {note_id} not found for user {user_id}")

        category, _ = await self.classify_text(full_text)
        title, summary = await self.generate_note_metadata(full_text, category=category)

        updated_data = {
            "id": note.id,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "full_text": full_text,
            "created_at": note.created_at,
        }

        await self.repo.update_note(note_id, updated_data)
        await self.session.commit()

        # Обновляем в search-service
        try:
            await self._call_search(
                "POST",
                "/insert",
                {
                    "note_id": note_id,
                    "user_id": user_id,
                    "text": full_text,
                    "title": title,
                    "summary": summary,
                    "category": category,
                },
            )
        except Exception as exc:
            logger.warning("Search service update failed: %s", exc)

        updated_note = await self.repo.get_note_by_id(user_id, note_id)
        if updated_note:
            note_schema = NoteSchema.model_validate(updated_note)
            await redis_manager.set_value(
                note_id, note_schema.model_dump_json(), ttl=300
            )

    async def delete_note(self, user_id: int, note_id: int) -> None:
        """Удалить заметку."""
        note = await self.repo.get_note_by_id(user_id, note_id)
        if note is None:
            raise NoteStorageError(f"Note {note_id} not found for user {user_id}")

        await self.repo.delete_note(note_id)
        await self.session.commit()

        # Удаляем из search-service
        try:
            await self._call_search("DELETE", f"/{note_id}")
        except Exception as exc:
            logger.warning("Search service delete failed: %s", exc)

        await redis_manager.delete_value(note_id)

    async def process_text(
        self, user_id: int, full_text: str, category: str | None = None
    ) -> dict:
        """Основной метод: классификация + создание или поиск."""
        if category is None:
            category, _ = await self.classify_text(full_text)

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