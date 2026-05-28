from src.main import app  # noqa: E402


class TestCreateNoteAPI:

    async def test_create_note_success(self, ac):
        """POST /notes/process — успешное создание заметки."""
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