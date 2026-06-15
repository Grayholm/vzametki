"""Интеграционные тесты API.

Тестируют связку API → сервис → БД.
Qdrant, Redis, Groq, Embedding замоканы.
Postgres — реальный.

Запуск: set MODE=test&& pytest tests/integration/ -v
"""


class TestCreateNote:
    """POST /notes/process → action == "created_note" """

    async def test_create_note_success(self, ac):
        """Успешное создание заметки."""
        response = await ac.post(
            "/notes/process",
            json={"user_id": 42, "text": "Тестовая заметка", "category": "Note"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "created_note"
        assert data["category"] == "Note"
        note = data["note"]
        assert note["note_id"] == 1
        assert note["title"] == "Тестовый заголовок"
        assert note["summary"] == "Тестовое резюме"

    async def test_create_multiple_notes_increment_id(self, ac):
        """Создание двух заметок — id увеличивается."""
        await ac.post(
            "/notes/process",
            json={"user_id": 42, "text": "Первая", "category": "Note"},
        )
        response = await ac.post(
            "/notes/process",
            json={"user_id": 42, "text": "Вторая", "category": "Note"},
        )

        data = response.json()
        assert data["note"]["note_id"] == 3


class TestSearch:
    """POST /notes/process с category=Search"""

    async def test_search_no_results_same_user(self, ac):
        """Поиск у пользователя, у которого нет заметок — пустой результат."""
        response = await ac.post(
            "/notes/process",
            json={"user_id": 99, "text": "запрос", "category": "Search"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "search"
        assert data["search"]["results"] == []


class TestListAll:
    """GET /notes/{user_id}/list"""

    async def test_list_all_no_notes(self, ac):
        """Пока нет заметок — пустой список."""
        response = await ac.get("/notes/999/list")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "list_all"
        assert data["notes"] == []


class TestGetById:
    """GET /notes/{user_id}/{note_id}"""

    async def test_get_note_by_id_not_found(self, ac):
        """Несуществующая заметка."""
        response = await ac.get("/notes/42/9999")

        assert response.status_code == 200
        data = response.json()
        assert data["note"] is None
        assert data["action"] == "get_by_id"

    async def test_get_note_by_id_existing(self, ac):
        """Существующая заметка."""
        response_note = await ac.post(
            "/notes/process",
            json={"user_id": 10, "text": "Найди меня", "category": "Note"},
        )

        data_note = response_note.json()["note"]
        print(data_note)
        note_id = data_note["note_id"]

        response = await ac.get(f"/notes/10/{note_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["note"] is not None
        assert data["note"]["id"] == note_id
        assert data["note"]["user_id"] == 10
        assert data["action"] == "get_by_id"


class TestUpdate:
    """PUT /notes/{user_id}/{note_id}"""

    async def test_update_not_found(self, ac):
        """Обновление несуществующей заметки."""
        response = await ac.put(
            "/notes/42/9999",
            json={"full_text": "Новый текст"},
        )

        assert response.status_code == 500  # NoteStorageError → 500

    async def test_update_success(self, ac):
        """Успешное обновление."""
        response_note = await ac.post(
            "/notes/process",
            json={"user_id": 20, "text": "Старый текст", "category": "Note"},
        )

        data_note = response_note.json()["note"]
        note_id = data_note["note_id"]

        response = await ac.put(
            f"/notes/20/{note_id}",
            json={"full_text": "Новый текст"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "updated"
        assert data["note_id"] == note_id


class TestDelete:
    """DELETE /notes/{user_id}/{note_id}"""

    async def test_delete_not_found(self, ac):
        """Удаление несуществующей заметки."""
        response = await ac.delete("/notes/42/9999")

        assert response.status_code == 500  # NoteStorageError → 500

    async def test_delete_success(self, ac):
        """Успешное удаление."""
        # Сначала создаём
        response_note = await ac.post(
            "/notes/process",
            json={"user_id": 30, "text": "Удали меня", "category": "Note"},
        )

        data_note = response_note.json()["note"]
        note_id = data_note["note_id"]

        response = await ac.delete(f"/notes/30/{note_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "deleted"
        assert data["note_id"] == note_id

        # Проверяем, что заметки больше нет
        get_response = await ac.get("/notes/30/1")
        assert get_response.json()["note"] is None


class TestClassify:
    """POST /notes/classify"""

    async def test_classify_message(self, ac):
        """Классификация текста."""
        
        response = await ac.post(
            "/notes/classify",
            json={"user_id": 1, "text": "Мне нужно купить продукты, а именно молоко, морковь, творог и ОБЯЗАТЕЛЬНО куриную грудку"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Note"