import os
import sys
import asyncio

from aiogram import Bot, Dispatcher
from loguru import logger

from config import BOT_TOKEN, TEST_MODE
from utils import setup_logging, init_db, close_db
from handlers import setup_routers
from scheduler import start_scheduler, scheduler


async def main():
    setup_logging(level="INFO")

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in .env")
        sys.exit(1)

    os.makedirs("data", exist_ok=True)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(setup_routers())

    await init_db()
    start_scheduler(bot)

    if TEST_MODE:
        logger.warning("TEST_MODE is ON — WEEX API calls are bypassed")
    logger.info("Bot started")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "chat_member", "chat_join_request"])
    finally:
        scheduler.shutdown()
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
