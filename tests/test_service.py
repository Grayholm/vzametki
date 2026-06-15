from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import AppError, DatabaseError, NoteStorageError


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
        ],
    )
    async def test_classify_text(
        self,
        notes_service,
        input_text,
        expected_category,
        expected_note_id,
    ):
        """Проверяет классификацию текста для всех категорий."""

        async def classify_side_effect(path: str, payload: dict) -> dict:
            text = payload.get("text", "")
            if "найди" in text.lower() or "ищи" in text.lower():
                return {"category": "Search"}
            if "покажи все" in text.lower() or "список" in text.lower():
                return {"category": "ListAll"}
            if "открой" in text.lower() or "заметку" in text.lower():
                return {"category": "GetById", "note_id": 5}
            if "привет" in text.lower() or "как дела" in text.lower():
                return {"category": "Trash"}
            return {"category": "Note"}

        notes_service._call_ai = AsyncMock(side_effect=classify_side_effect)

        category, note_id = await notes_service.classify_text(input_text)
        assert category == expected_category
        assert note_id == expected_note_id
        notes_service._call_ai.assert_called_once_with("/classify", {"text": input_text})


class TestGenerateMetadata:
    @pytest.mark.parametrize(
        "full_text, expected_title, expected_summary",
        [
            (
                "Это тестовая заметка для проверки генерации метаданных.",
                "Тестовый заголовок",
                "Тестовое краткое содержание.",
            ),
            (
                "Еще одна заметка с другим текстом для проверки.",
                "Другой тестовый заголовок",
                "Другое тестовое краткое содержание.",
            ),
        ],
    )
    async def test_generate_note_metadata(
        self,
        notes_service,
        full_text,
        expected_title,
        expected_summary,
    ):
        """Проверяет генерацию заголовка и краткого содержания."""

        notes_service._call_ai = AsyncMock(
            return_value={
                "title": expected_title,
                "summary": expected_summary,
            }
        )

        title, summary = await notes_service.generate_note_metadata(full_text)
        assert title == expected_title
        assert summary == expected_summary
        notes_service._call_ai.assert_called_once_with(
            "/generate-metadata",
            {"text": full_text, "category": None},
        )


class TestCreateNote:
    PAYLOAD = {"user_id": 1, "full_text": "Текст заметки", "category": "Note"}

    async def _setup_mocks(self, notes_service):
        notes_service._call_ai = AsyncMock(
            return_value={
                "title": "Заголовок",
                "summary": "Резюме",
            }
        )
        notes_service.repo.create_note = AsyncMock(return_value=1)
        # Мокаем продюсера RabbitMQ
        with patch("src.core.service.event_producer.publish", new_callable=AsyncMock) as mock_publish:
            self.mock_publish = mock_publish

    async def test_success(self, notes_service, mock_notes_repo):
        """Успешное создание заметки."""
        await self._setup_mocks(notes_service)

        note = await notes_service.create_note(self.PAYLOAD)

        assert note["note_id"] == 1
        assert note["title"] == "Заголовок"
        assert note["summary"] == "Резюме"
        assert note["category"] == "Note"
        mock_notes_repo.create_note.assert_awaited_once()

    async def test_db_error(self, notes_service, mock_notes_repo):
        """DatabaseError пробрасывается из репозитория."""
        await self._setup_mocks(notes_service)
        mock_notes_repo.create_note = AsyncMock(side_effect=DatabaseError("DB error"))

        with pytest.raises(DatabaseError):
            await notes_service.create_note(self.PAYLOAD)


class TestSearchNotes:
    async def test_search_notes(self, notes_service):
        """Проверяет поиск заметок по запросу."""
        notes_service._call_qdrant = AsyncMock(
            return_value={
                "results": [
                    {"id": 1, "payload": {"title": "Заметка 1", "summary": "Резюме 1"}},
                    {"id": 2, "payload": {"title": "Заметка 2", "summary": "Резюме 2"}},
                ]
            }
        )

        result = await notes_service.search_notes(user_id=1, query="Найди заметки по биологии")

        assert result["query"] == "Найди заметки по биологии"
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == 1
        assert result["results"][0]["payload"]["title"] == "Заметка 1"
        notes_service._call_qdrant.assert_called_once_with(
            "POST", "/search",
            {"user_id": 1, "query": "Найди заметки по биологии"},
        )

    async def test_search_notes_no_results(self, notes_service):
        """Поиск возвращает пустой список."""
        notes_service._call_qdrant = AsyncMock(return_value={"results": []})

        result = await notes_service.search_notes(user_id=1, query="несуществующий текст")

        assert len(result["results"]) == 0

    async def test_search_notes_error(self, notes_service):
        """При ошибке поиска возвращается пустой список."""
        notes_service._call_qdrant = AsyncMock(side_effect=Exception("Search failed"))

        result = await notes_service.search_notes(user_id=1, query="ошибка")

        assert result["query"] == "ошибка"
        assert result["results"] == []


class TestListAllNotes:
    async def test_list_all_notes(self, notes_service):
        """Список всех заметок."""
        notes_service._call_qdrant = AsyncMock(
            return_value={
                "notes": [
                    {"id": 1, "payload": {"title": "Заметка 1", "summary": "Резюме 1"}},
                    {"id": 2, "payload": {"title": "Заметка 2", "summary": "Резюме 2"}},
                ]
            }
        )

        result = await notes_service.list_all_notes(user_id=1)

        assert result["category"] == "ListAll"
        assert result["action"] == "list_all"
        assert len(result["notes"]) == 2
        assert result["notes"][0]["id"] == 1
        assert result["notes"][1]["payload"]["title"] == "Заметка 2"

    async def test_list_all_notes_error(self, notes_service):
        """При ошибке возвращается пустой список."""
        notes_service._call_qdrant = AsyncMock(side_effect=Exception("error"))

        result = await notes_service.list_all_notes(user_id=1)

        assert result["notes"] == []


class TestGetNoteById:
    async def test_get_note_by_id(self, notes_service, mock_redis):
        """Получение заметки по ID (из БД)."""
        mock_redis.get_value = AsyncMock(return_value=None)
        notes_service.repo.get_note_by_id = AsyncMock(
            return_value={
                "id": 1,
                "user_id": 14,
                "title": "Заметка 1",
                "summary": "Резюме 1",
                "full_text": "Полный текст заметки",
                "created_at": "2024-01-01T12:00:00",
            }
        )
        # Мокаем redis_manager на уровне модуля
        with patch("src.core.service.redis_manager") as mock_redis_manager:
            mock_redis_manager.get_value = AsyncMock(return_value=None)
            mock_redis_manager.set_value = AsyncMock()

            result = await notes_service.get_note_by_id(user_id=14, note_id=1)

        assert result["category"] == "GetById"
        assert result["action"] == "get_by_id"
        assert result["note"]["id"] == 1

    async def test_get_note_by_id_not_found(self, notes_service):
        """Заметка не найдена."""
        with patch("src.core.service.redis_manager") as mock_redis_manager:
            mock_redis_manager.get_value = AsyncMock(return_value=None)
            notes_service.repo.get_note_by_id = AsyncMock(return_value=None)

            result = await notes_service.get_note_by_id(user_id=14, note_id=999)

        assert result is None

    async def test_get_note_by_id_error(self, notes_service):
        """При ошибке возвращается None."""
        with patch("src.core.service.redis_manager") as mock_redis_manager:
            mock_redis_manager.get_value = AsyncMock(side_effect=Exception("error"))
            notes_service.repo.get_note_by_id = AsyncMock(return_value=None)

            result = await notes_service.get_note_by_id(user_id=14, note_id=1)

        assert result is None


class TestUpdateNote:
    async def test_update_note_success(self, notes_service, mock_notes_repo):
        """Успешное обновление заметки."""
        mock_notes_repo.get_note_by_id = AsyncMock(
            return_value=MagicMock(
                id=1,
                user_id=14,
                title="Старый",
                summary="Старое",
                full_text="Старый текст",
                created_at="2024-01-01T12:00:00",
            )
        )
        notes_service._call_ai = AsyncMock(
            side_effect=[
                {"category": "Note"},  # classify_text
                {"title": "Новый заголовок", "summary": "Новое резюме"},  # generate_note_metadata
            ]
        )

        with (
            patch("src.core.service.redis_manager") as mock_redis_manager,
            patch("src.core.service.event_producer.publish", new_callable=AsyncMock) as mock_publish,
        ):
            mock_redis_manager.set_value = AsyncMock()

            await notes_service.update_note(
                user_id=14, note_id=1, full_text="Новый текст заметки"
            )

        mock_notes_repo.update_note.assert_awaited_once()
        mock_publish.assert_awaited_once()

    async def test_update_note_not_found(self, notes_service, mock_notes_repo):
        """Если заметка не найдена — NoteStorageError."""
        mock_notes_repo.get_note_by_id = AsyncMock(return_value=None)

        with pytest.raises(NoteStorageError):
            await notes_service.update_note(user_id=14, note_id=999, full_text="Текст")


class TestDeleteNote:
    async def test_delete_note_success(self, notes_service, mock_notes_repo):
        """Успешное удаление заметки."""
        mock_notes_repo.get_note_by_id = AsyncMock(
            return_value=MagicMock(
                id=1,
                user_id=14,
                title="Заметка 1",
                summary="Резюме 1",
                full_text="Полный текст",
                created_at="2024-01-01T12:00:00",
            )
        )

        with (
            patch("src.core.service.redis_manager") as mock_redis_manager,
            patch("src.core.service.event_producer.publish", new_callable=AsyncMock) as mock_publish,
        ):
            mock_redis_manager.delete_value = AsyncMock()

            await notes_service.delete_note(user_id=14, note_id=1)

        mock_notes_repo.delete_note.assert_awaited_once_with(1)
        mock_publish.assert_awaited_once()
        mock_redis_manager.delete_value.assert_awaited_once_with(1)

    async def test_delete_note_not_found(self, notes_service, mock_notes_repo):
        """Заметка не найдена."""
        mock_notes_repo.get_note_by_id = AsyncMock(return_value=None)

        with pytest.raises(NoteStorageError):
            await notes_service.delete_note(user_id=14, note_id=999)


class TestProcessText:
    PAYLOAD = {"user_id": 14, "full_text": "Тестовый текст"}

    async def test_process_text_created_note(self, notes_service, mock_notes_repo):
        """При Note создаётся заметка."""
        notes_service._call_ai = AsyncMock(
            return_value={"title": "Заголовок 1", "summary": "Краткий пересказ 1"}
        )
        mock_notes_repo.create_note = AsyncMock(return_value=1)

        with patch("src.core.service.event_producer.publish", new_callable=AsyncMock):
            result = await notes_service.process_text(
                user_id=self.PAYLOAD["user_id"],
                full_text=self.PAYLOAD["full_text"],
                category="Note",
            )

        assert result["category"] == "Note"
        assert result["action"] == "created_note"
        assert result["note"]["note_id"] == 1

    async def test_process_text_search(self, notes_service):
        """При Search выполняется поиск."""
        notes_service._call_qdrant = AsyncMock(
            return_value={
                "results": [{"id": 1, "payload": {"title": "Заметка 1"}}]
            }
        )

        result = await notes_service.process_text(
            user_id=self.PAYLOAD["user_id"],
            full_text="Найди заметки про тренировки",
            category="Search",
        )

        assert result["action"] == "search"

    async def test_process_text_trash(self, notes_service):
        """При Trash возвращается сообщение о мусоре."""
        result = await notes_service.process_text(
            user_id=self.PAYLOAD["user_id"],
            full_text="Привет",
            category="Trash",
        )

        assert result["action"] == "trash"