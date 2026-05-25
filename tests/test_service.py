from unittest.mock import AsyncMock

import pytest


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
    async def test_classify_note(self, notes_service, mock_groq_client, input_text, expected_category, expected_note_id):
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

        category, note_id = await notes_service.classify_text(
            input_text
        )
        assert category == expected_category
        assert note_id == expected_note_id


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
        full_text = full_text
        expected_title = expected_title
        expected_summary = expected_summary

        async def metadata_side_effect(content: str, category: str | None = None) -> dict:
            return {
                "title": expected_title,
                "summary": expected_summary,
            }
        
        mock_groq_client.generate_note_title_summary = AsyncMock(side_effect=metadata_side_effect)

        title, summary = await notes_service.generate_note_metadata(full_text)

        assert title == expected_title
        assert summary == expected_summary