import asyncio
import logging
from src.bot.config import bot, dp
from src.bot.handlers.router import notes_router

async def run_bot():
    logging.basicConfig(level=logging.INFO)
    
    dp.include_router(notes_router)
    
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run_bot())