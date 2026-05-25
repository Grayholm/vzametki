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
    async def test_classify_note(self, notes_service, input_text, expected_category, expected_note_id):
        """Проверяет классификацию текста для всех категорий."""

        category, note_id = await notes_service.classify_text(
            input_text
        )
        assert category == expected_category
        assert note_id == expected_note_id