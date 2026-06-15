from dataclasses import dataclass

import logging
import httpx

from src.config import settings
from src.core.qdrant_client import qdrant_client

logger = logging.getLogger(__name__)

@dataclass
class NoteEventHandler:
    """Обработчик событий заметок из RabbitMQ."""
    def __init__(self):
        self.qdrant_client = qdrant_client

    async def _handle_insert_update(self, body: dict) -> None:
        """Обработка создания или обновления заметки."""
        try:
            text = body.get("full_text", body.get("text", ""))

            # 1. Получаем эмбеддинг от ai-service
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.AI_SERVICE_URL}/embed",
                    json={"text": text},
                )
            resp.raise_for_status()
            vector = resp.json()["vector"]

            # 2. Сохраняем в Qdrant
            await qdrant_client.insert_note_vector(
                note_id=body["note_id"],
                vector=vector,
                payload={
                    "user_id": body["user_id"],
                    "title": body.get("title", ""),
                    "summary": body.get("summary", ""),
                    "category": body.get("category", ""),
                },
            )
            logger.info("Successfully processed event for note %s", body["note_id"])
        except Exception as exc:
            logger.error("Failed to handle insert/update for note %s: %s", body.get("note_id"), exc)

    async def _handle_delete(self, note_id: int) -> None:
        """Обработка удаления заметки."""
        try:
            await qdrant_client.delete_note_vector(note_id)
            logger.info("Successfully deleted vector for note %s", note_id)
        except Exception as exc:
            logger.error("Failed to delete vector for note %s: %s", note_id, exc)