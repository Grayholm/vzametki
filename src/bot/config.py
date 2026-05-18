from aiogram import Bot, Dispatcher

from src.database.config import settings


bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()