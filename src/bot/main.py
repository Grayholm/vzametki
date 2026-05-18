import asyncio
import logging

from src.bot.config import bot, dp
from src.bot.handlers.router import notes_router
from src.bot.middlewares.rate_limit import RateLimitMiddleware


async def run_bot():
    logging.basicConfig(level=logging.INFO)
    
    dp.message.middleware(RateLimitMiddleware())
    dp.include_router(notes_router)
    
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run_bot())
