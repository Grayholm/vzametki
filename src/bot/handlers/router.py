from aiogram import Router, types
from aiogram.filters import CommandStart

from src.bot.handlers.handlers import create_note
from src.ai.groq_client import groq_client


notes_router = Router()

@notes_router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.full_name}! Я помогу тебе управлять твоими заметками. Просто отправь текст, а я сохраню его для тебя.")

async def handle_note_message(message: types.Message):
    payload = {
        "full_text": message.text
    }

    try:
        response = await create_note(message.from_user.id, payload)
        await message.answer(
            f"Заметка сохранена!\n\nID: {response.get('note_id')}\nЗаголовок: {response.get('title')}\nРезюме: {response.get('summary')}"
        )
    except Exception as e:
        await message.answer("Произошла ошибка при сохранении заметки. Пожалуйста, попробуй позже.")
        return
    
async def handle_search_message(message: types.Message):
    pass

async def handle_trash_message(message: types.Message):
    pass

@notes_router.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст заметки.")
        return

    classification = await groq_client.classify_note_content(message.text)

    match classification:
        case "Note":
            await handle_note_message(message)
        case "Search":
            await handle_search_message(message)
        case "Trash":
            await handle_trash_message(message)
        case _:
            await message.answer("Не удалось классифицировать сообщение. Пожалуйста, попробуй переформулировать.")