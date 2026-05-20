from aiogram import Router, types
from aiogram.filters import CommandStart

from src.bot.handlers.handlers import process_message


notes_router = Router()

@notes_router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.full_name}! Я помогу тебе управлять твоими заметками. Просто отправь текст, а я сохраню его для тебя.")

@notes_router.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст заметки.")
        return

    try:
        response = await process_message(message.from_user.id, message.text)
    except Exception as e:
        await message.answer("Произошла ошибка при обработке сообщения. Пожалуйста, попробуй позже.")
        print(f"Ошибка при обработке сообщения: {e}")
        return

    action = response.get("action")

    if action == "created_note":
        note = response.get("note", {})
        await message.answer(
            f"Заметка сохранена!\n\nКатегория: {response.get('category')}\nID: {note.get('note_id')}\nЗаголовок: {note.get('title')}\nРезюме: {note.get('summary')}"
        )
        return

    if action == "search":
        results = response.get("search", {}).get("results", [])
        if not results:
            await message.answer("Ничего не найдено по вашему запросу.")
            return

        text = "Результаты поиска:\n"
        for item in results[:5]:
            payload = item.get("payload", {})
            title = payload.get("title")
            summary = payload.get("summary")
            text += f"\nID: {item.get('id')}\nЗаголовок: {title}\nРезюме: {summary}\n"
        await message.answer(text)
        return

    await message.answer(response.get("message", "Сообщение не похоже на заметку или запрос поиска."))