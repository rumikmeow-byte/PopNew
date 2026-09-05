import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
from admin_handlers import admin_router
from user_handlers import handlers_router

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(handlers_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
