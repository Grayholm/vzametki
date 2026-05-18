from aiogram import Router, types
from aiogram.filters import CommandStart

from src.bot.handlers.handlers import create_note


notes_router = Router()

@notes_router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.full_name}! Я помогу тебе управлять твоими заметками. Просто отправь текст, а я сохраню его для тебя.")

@notes_router.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст заметки.")
        return

    payload = {
        "full_text": message.text
    }

    try:
        await create_note(message.from_user.id, payload)
        await message.answer("Заметка успешно сохранена!")
    except Exception as e:
        await message.answer("Произошла ошибка при сохранении заметки. Пожалуйста, попробуй позже.")
        return