from unittest.mock import AsyncMock, MagicMock

import pytest

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