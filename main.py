import asyncio
import os
import asyncpg
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from gift_modules import register_handlers, init_db_tables

# Загружаем переменные из локального .env файла (если он есть)
load_dotenv()

# Получаем токен и URL базы данных из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Переменная BOT_TOKEN не найдена! Укажите её в .env или в Environment Variables на Render.")

async def main():
    # 1. Инициализация подключения к БД
    # Если DATABASE_URL указан (на Render для PostgreSQL)
    if DATABASE_URL:
        # Для Render/Heroku часто нужен параметр ssl для PostgreSQL
        db_pool = await asyncpg.create_pool(dsn=DATABASE_URL)
        print("Успешно подключились к базе данных PostgreSQL!")
    else:
        # Локальный фолбек на SQLite, если PostgreSQL не настроен
        db_pool = await aiosqlite.connect("database.db")
        print("DATABASE_URL не найден. Инициализирована локальная база данных SQLite (database.db).")

    # 2. Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Прокидываем db_pool в контекст хэндлеров aiogram 3
    dp["db_pool"] = db_pool

    # 3. Инициализируем таблицы в БД и подключаем модуль
    await init_db_tables(db_pool)
    register_handlers(dp)

    print("Бот успешно запущен!")

    try:
        # Запускаем поллинг
        await dp.start_polling(bot)
    finally:
        # Корректное закрытие соединений при остановке бота
        if DATABASE_URL:
            await db_pool.close()
        else:
            await db_pool.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
