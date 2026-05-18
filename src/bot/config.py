from aiogram import Bot, Dispatcher

from src.database.config import settings
from src.bot.handlers.router import notes_router

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

dp.include_router(notes_router)