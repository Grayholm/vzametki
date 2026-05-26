import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import json

from src.exceptions import AppError, DatabaseError, EmbeddingError, NoteStorageError, VectorStoreError


class TestClassifyText:

    @pytest.mark.parametrize(
            "input_text, expected_category, expected_note_id",
            [
                ("Завтра нужно сделать доклад по биологии", "Note", None),
                ("Найди что я писал про тренировки", "Search", None),
                ("Покажи все мои заметки", "ListAll", None),
                ("Открой заметку 5", "GetById", 5),
                ("Привет", "Trash", None),
                ("как дела", "Trash", None),
            ]
    )
    async def test_classify_text(self, notes_service, mock_groq_client, input_text, expected_category, expected_note_id):
        """Проверяет классификацию текста для всех категорий."""

        async def classify_side_effect(text: str) -> dict:
            if "найди" in text.lower() or "ищи" in text.lower():
                return {"category": "Search"}
            if "покажи все" in text.lower() or "список" in text.lower():
                return {"category": "ListAll"}
            if "открой" in text.lower() or "заметку" in text.lower():
                return {"category": "GetById", "note_id": 5}
            if "привет" in text.lower() or "как дела" in text.lower():
                return {"category": "Trash"}
            return {"category": "Note"}

        mock_groq_client.classify_note_content = AsyncMock(side_effect=classify_side_effect)

        category, note_id = await notes_service.classify_text(input_text)
        assert category == expected_category
        assert note_id == expected_note_id
        assert notes_service.groq_client.classify_note_content.call_count == 1
        assert notes_service.groq_client.classify_note_content.call_args[0][0] == input_text


class TestGenerateMetadata:

    @pytest.mark.parametrize(
        "full_text, expected_title, expected_summary",
        [
            (
                "Это тестовая заметка для проверки генерации метаданных.",
                "Тестовый заголовок",
                "Тестовое краткое содержание."
            ),
            (
                "Еще одна заметка с другим текстом для проверки.",
                "Другой тестовый заголовок",
                "Другое тестовое краткое содержание."
            ),

        ]
    )
    async def test_generate_note_metadata(self, notes_service, mock_groq_client, full_text, expected_title, expected_summary):
        """Проверяет генерацию заголовка и краткого содержания."""

        mock_groq_client.generate_note_title_summary = AsyncMock(return_value={
            "title": expected_title,
            "summary": expected_summary,
        })

        title, summary = await notes_service.generate_note_metadata(full_text)
        assert title == expected_title
        assert summary == expected_summary
        assert notes_service.groq_client.generate_note_title_summary.call_count == 1
        assert notes_service.groq_client.generate_note_title_summary.call_args[0][0] == full_text


class TestCreateNote:

    PAYLOAD = {"user_id": 1, "full_text": "Текст заметки", "category": "Note"}

    async def _setup_mocks(
        self,
        mock_groq_client,
        mock_notes_repo,
        mock_embedding,
        mock_qdrant,
    ):
        mock_groq_client.generate_note_title_summary = AsyncMock(return_value={
            "title": "Заголовок", "summary": "Резюме",
        })
        mock_notes_repo.create_note = AsyncMock(return_value=1)
        mock_embedding.embed_text = MagicMock(return_value=[0.1] * 384)
        mock_qdrant.insert_note_vector = AsyncMock()

    async def test_success(self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant):
        """Успешное создание заметки."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)

        note = await notes_service.create_note(self.PAYLOAD)

        assert note["note_id"] == 1
        assert note["title"] == "Заголовок"
        assert note["summary"] == "Резюме"
        assert note["category"] == "Note"
        mock_notes_repo.create_note.assert_awaited_once()
        mock_qdrant.insert_note_vector.assert_awaited_once()

    async def test_db_error(self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant):
        """DatabaseError пробрасывается из репозитория."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_notes_repo.create_note = AsyncMock(side_effect=DatabaseError("DB error"))

        with pytest.raises(DatabaseError):
            await notes_service.create_note(self.PAYLOAD)

    async def test_embedding_error_propagates(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """EmbeddingError (наследует AppError) пробрасывается как есть."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_embedding.embed_text.side_effect = EmbeddingError("embed failed")

        with pytest.raises(EmbeddingError):
            await notes_service.create_note(self.PAYLOAD)

    async def test_unexpected_embedding_error_raises_note_storage_error(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """Неожиданная ошибка embed_text (не AppError) → NoteStorageError."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_embedding.embed_text.side_effect = RuntimeError("unexpected")

        with pytest.raises(NoteStorageError):
            await notes_service.create_note(self.PAYLOAD)

    async def test_vector_store_error(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """VectorStoreError (наследует AppError) пробрасывается."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_qdrant.insert_note_vector = AsyncMock(side_effect=VectorStoreError("Qdrant error"))

        with pytest.raises(VectorStoreError):
            await notes_service.create_note(self.PAYLOAD)

    async def test_app_error_from_qdrant_propagates(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """Любая AppError из Qdrant пробрасывается."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_qdrant.insert_note_vector = AsyncMock(side_effect=AppError("App error"))

        with pytest.raises(AppError):
            await notes_service.create_note(self.PAYLOAD)

    async def test_unexpected_qdrant_error_raises_note_storage_error(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """Неожиданная ошибка Qdrant (не AppError) → NoteStorageError."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_qdrant.insert_note_vector = AsyncMock(side_effect=Exception("unexpected"))

        with pytest.raises(NoteStorageError):
            await notes_service.create_note(self.PAYLOAD)


class TestSearchNotes:
    def _setup_mocks(self, mock_embedding, mock_qdrant):
        mock_embedding.embed_text = MagicMock(return_value=[0.1] * 384)
        mock_qdrant.search_similar_notes = AsyncMock(return_value=[
            {"note_id": 1, "payload": {"title": "Заметка 1", "summary": "Резюме 1"}},
            {"note_id": 2, "payload": {"title": "Заметка 2", "summary": "Резюме 2"}},
        ])


    async def test_search_notes(self, notes_service, mock_embedding, mock_qdrant):
        """Проверяет поиск заметок по запросу."""
        self._setup_mocks(mock_embedding, mock_qdrant)

        result = await notes_service.search_notes(user_id=1, query="Найди заметки по биологии", top_k=5)

        assert result["query"] == "Найди заметки по биологии"
        assert len(result["results"]) == 2
        assert result["results"][0]["note_id"] == 1
        assert result["results"][0]["payload"]["title"] == "Заметка 1"
        assert result["results"][0]["payload"]["summary"] == "Резюме 1"
        assert result["results"][1]["note_id"] == 2
        assert result["results"][1]["payload"]["title"] == "Заметка 2"
        assert result["results"][1]["payload"]["summary"] == "Резюме 2"
        mock_embedding.embed_text.assert_called_once_with("Найди заметки по биологии")
        mock_qdrant.search_similar_notes.assert_awaited_once_with(1, [0.1] * 384, top_k=5)

    
    async def test_search_notes_no_query(self, notes_service, mock_qdrant):
        """Проверяет поиск заметок без запроса (только по user_id)."""
        mock_qdrant.search_similar_notes = AsyncMock(return_value=[
            {"note_id": 1, "payload": {"title": "Заметка 1", "summary": "Резюме 1"}},
            {"note_id": 2, "payload": {"title": "Заметка 2", "summary": "Резюме 2"}},
            {"note_id": 3, "payload": {"title": "Заметка 3", "summary": "Резюме 3"}},
        ])

        result = await notes_service.search_notes(user_id=1, query=None, top_k=5)

        assert len(result["results"]) == 3
        assert result["results"][0]["note_id"] == 1
        assert result["results"][0]["payload"]["title"] == "Заметка 1"
        assert result["results"][0]["payload"]["summary"] == "Резюме 1"
        assert result["results"][1]["note_id"] == 2
        assert result["results"][1]["payload"]["title"] == "Заметка 2"
        assert result["results"][1]["payload"]["summary"] == "Резюме 2"
        assert result["results"][2]["note_id"] == 3
        assert result["results"][2]["payload"]["title"] == "Заметка 3"
        assert result["results"][2]["payload"]["summary"] == "Резюме 3"
        mock_qdrant.search_similar_notes.assert_awaited_once_with(1, top_k=5)

    
    async def test_search_notes_embedding_error(self, notes_service, mock_embedding):
        """Проверяет, что ошибка при генерации вектора запроса пробрасывается."""
        mock_embedding.embed_text = MagicMock(side_effect=EmbeddingError("Embedding failed"))

        with pytest.raises(EmbeddingError):
            await notes_service.search_notes(user_id=1, query="Найди заметки по биологии", top_k=5)
        
        assert mock_embedding.embed_text.call_count == 1
        assert mock_embedding.embed_text.call_args[0][0] == "Найди заметки по биологии"


    async def test_search_notes_qdrant_error(self, notes_service, mock_embedding, mock_qdrant):
        """Проверяет, что ошибка при поиске в Qdrant пробрасывается."""
        mock_embedding.embed_text = MagicMock(return_value=[0.1] * 384)
        mock_qdrant.search_similar_notes = AsyncMock(side_effect=VectorStoreError("Qdrant error"))

        with pytest.raises(VectorStoreError):
            await notes_service.search_notes(user_id=1, query="Найди заметки по биологии", top_k=5)
        
        assert mock_embedding.embed_text.call_count == 1
        assert mock_embedding.embed_text.call_args[0][0] == "Найди заметки по биологии"
        assert mock_qdrant.search_similar_notes.call_count == 1
        assert mock_qdrant.search_similar_notes.call_args[0][0] == 1
        assert mock_qdrant.search_similar_notes.call_args[0][1] == [0.1] * 384


class TestListAllNotes:
    def _setup_mocks(self, mock_qdrant):
        mock_qdrant.scroll_notes_by_user_id = AsyncMock(return_value=[
            {"note_id": 1, "payload": {"title": "Заметка 1", "summary": "Резюме 1"}},
            {"note_id": 2, "payload": {"title": "Заметка 2", "summary": "Резюме 2"}},
        ])

    
    async def test_list_all_notes(self, notes_service, mock_qdrant):
        self._setup_mocks(mock_qdrant)

        result = await notes_service.list_all_notes(user_id=1)

        assert result["category"] == "ListAll"
        assert result["action"] == "list_all"
        assert len(result["notes"]) == 2
        assert result["notes"][0]["note_id"] == 1
        assert result["notes"][0]["payload"]["title"] == "Заметка 1"
        assert result["notes"][0]["payload"]["summary"] == "Резюме 1"
        assert result["notes"][1]["note_id"] == 2
        assert result["notes"][1]["payload"]["title"] == "Заметка 2"
        assert result["notes"][1]["payload"]["summary"] == "Резюме 2"
        mock_qdrant.scroll_notes_by_user_id.assert_awaited_once_with(1, limit=100)

    
    async def test_list_all_notes_qdrant_error(self, notes_service, mock_qdrant):
        """Проверяет, что при ошибке Qdrant возвращается пустой список заметок."""
        mock_qdrant.scroll_notes_by_user_id = AsyncMock(side_effect=VectorStoreError("Qdrant error"))

        with pytest.raises(VectorStoreError):
            await notes_service.list_all_notes(user_id=1)

        assert mock_qdrant.scroll_notes_by_user_id.call_count == 1
        assert mock_qdrant.scroll_notes_by_user_id.call_args[0][0] == 1
    

    async def test_list_all_notes_unexpected_error(self, notes_service, mock_qdrant):
        """Проверяет, что при неожиданной ошибке Qdrant возвращается пустой словарь с notes=[]."""
        mock_qdrant.scroll_notes_by_user_id = AsyncMock(side_effect=RuntimeError("unexpected"))

        result = await notes_service.list_all_notes(user_id=1)

        assert result["category"] == "ListAll"
        assert result["notes"] == []

    async def test_list_all_notes_app_error(self, notes_service, mock_qdrant):
        """Проверяет, что при AppError из Qdrant ошибка пробрасывается."""
        mock_qdrant.scroll_notes_by_user_id = AsyncMock(side_effect=AppError("App error"))

        with pytest.raises(AppError):
            await notes_service.list_all_notes(user_id=1)

        assert mock_qdrant.scroll_notes_by_user_id.call_count == 1
        assert mock_qdrant.scroll_notes_by_user_id.call_args[0][0] == 1

class TestGetNoteById:
    def _setup_mocks(self, mock_notes_repo):
        mock_notes_repo.get_note_by_id = AsyncMock(return_value={
            "id": 1,
            "user_id": 14,
            "title": "Заметка 1",
            "summary": "Резюме 1",
            "full_text": "Полный текст заметки",
            "created_at": "2024-01-01T12:00:00"
        })

    
    @pytest.mark.parametrize(
        "cached_note",
        [
            None,
            json.dumps({
                "id": 1,
                "user_id": 14,
                "title": "Заметка 1",
                "summary": "Резюме 1",
                "full_text": "Полный текст заметки",
                "created_at": "2024-01-01T12:00:00"
            })
        ]
    )
    async def test_get_note_by_id(self, notes_service, mock_notes_repo, mock_redis, cached_note):
        self._setup_mocks(mock_notes_repo)

        mock_redis.get_value = AsyncMock(return_value=cached_note)

        result = await notes_service.get_note_by_id(user_id=14, note_id=1)

        assert result["category"] == "GetById"
        assert result["action"] == "get_by_id"
        result_note = result["note"]
        assert result_note["id"] == 1
        assert result_note["user_id"] == 14
        assert result_note["title"] == "Заметка 1"
        assert result_note["summary"] == "Резюме 1"
        assert result_note["full_text"] == "Полный текст заметки"
        assert result_note["created_at"] == datetime.datetime(2024, 1, 1, 12, 0)

        if cached_note:
            mock_notes_repo.get_note_by_id.assert_not_awaited()
        else:
            mock_notes_repo.get_note_by_id.assert_awaited_once()


    async def test_get_note_by_id_not_found(self, notes_service, mock_notes_repo, mock_redis):
        """Проверяет, что при отсутствии заметки возвращается None."""
        mock_notes_repo.get_note_by_id = AsyncMock(return_value=None)
        mock_redis.get_value = AsyncMock(return_value=None)

        result = await notes_service.get_note_by_id(user_id=14, note_id=999)

        assert result is None
        mock_notes_repo.get_note_by_id.assert_awaited_once_with(14, 999)

    
    async def test_get_note_by_id_database_error(self, notes_service, mock_notes_repo, mock_redis):
        """Проверяет, что при DatabaseError из репозитория пробрасывается DatabaseError."""
        mock_notes_repo.get_note_by_id = AsyncMock(side_effect=DatabaseError("DB error"))
        mock_redis.get_value = AsyncMock(return_value=None)

        with pytest.raises(DatabaseError):
            await notes_service.get_note_by_id(user_id=14, note_id=1)

        mock_notes_repo.get_note_by_id.assert_awaited_once_with(14, 1)

    
    async def test_get_note_by_id_unexpected_error(self, notes_service, mock_notes_repo, mock_redis):
        """Проверяет, что при неожиданной ошибке из репозитория возвращается None."""
        mock_notes_repo.get_note_by_id = AsyncMock(side_effect=Exception("unexpected"))
        mock_redis.get_value = AsyncMock(return_value=None)

        result = await notes_service.get_note_by_id(user_id=14, note_id=1)

        assert result is None
        mock_notes_repo.get_note_by_id.assert_awaited_once_with(14, 1)

    
    async def test_get_note_by_id_app_error(self, notes_service, mock_notes_repo, mock_redis):
        """Проверяет, что при AppError из репозитория пробрасывается AppError."""
        mock_notes_repo.get_note_by_id = AsyncMock(side_effect=AppError("App error"))
        mock_redis.get_value = AsyncMock(return_value=None)

        with pytest.raises(AppError):
            await notes_service.get_note_by_id(user_id=14, note_id=1)

        mock_notes_repo.get_note_by_id.assert_awaited_once_with(14, 1)


class TestProcessText:

    PAYLOAD = {"user_id": 14, "full_text": "Тестовый текст", "category": "Note"}

    async def _setup_mocks(self, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant):
        mock_groq_client.generate_note_title_summary = AsyncMock(return_value={
            "title": "Заголовок 1", "summary": "Краткий пересказ 1",
        })
        mock_notes_repo.create_note = AsyncMock(return_value=1)
        mock_embedding.embed_text = MagicMock(return_value=[0.1] * 384)
        mock_qdrant.insert_note_vector = AsyncMock()

    async def test_process_text_created_note(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """При Note создаётся заметка."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)

        result = await notes_service.process_text(
            user_id=self.PAYLOAD["user_id"],
            full_text=self.PAYLOAD["full_text"],
            category="Note",
        )

        assert result["category"] == "Note"
        assert result["action"] == "created_note"
        note = result["note"]
        assert note["note_id"] == 1
        assert note["title"] == "Заголовок 1"
        assert note["summary"] == "Краткий пересказ 1"
        assert note["category"] == "Note"
        mock_notes_repo.create_note.assert_awaited_once()

    async def test_process_text_search(
        self, notes_service, mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant
    ):
        """При Search выполняется поиск."""
        await self._setup_mocks(mock_groq_client, mock_notes_repo, mock_embedding, mock_qdrant)
        mock_qdrant.search_similar_notes = AsyncMock(return_value=[
            {"note_id": 1, "payload": {"title": "Заметка 1"}},
        ])

        result = await notes_service.process_text(
            user_id=self.PAYLOAD["user_id"],
            full_text="Найди заметки про тренировки",
            category="Search",
        )

        assert result["action"] == "search"

    async def test_process_text_trash(
        self, notes_service
    ):
        """При Trash возвращается сообщение о мусоре."""
        result = await notes_service.process_text(
            user_id=self.PAYLOAD["user_id"],
            full_text=self.PAYLOAD["full_text"],
            category="Trash",
        )

        assert result["action"] == "trash"
