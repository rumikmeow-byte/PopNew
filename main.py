import os
import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher
from gift_modules import register_handlers, init_db_tables

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    if not BOT_TOKEN:
        raise ValueError("Ошибка: BOT_TOKEN не задан в Environment Variables!")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключение к PostgreSQL
    db_pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    
    # Инициализация БД
    await init_db_tables(db_pool)

    # Прокидываем db_pool в хэндлеры
    dp["db_pool"] = db_pool
    register_handlers(dp)

    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
