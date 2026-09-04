import asyncio
from aiogram import Bot, Dispatcher
from gift_modules import register_handlers, init_db_tables

# Инициализация вашего подключения к БД (asyncpg pool)
# db_pool = await asyncpg.create_pool(...) 

async def main():
    bot = Bot(token="ВАШ_ТОКЕН")
    dp = Dispatcher()

    # Передача db_pool в хэндлеры через пропсы
    dp["db_pool"] = db_pool

    # Инициализируем таблицы и подключаем роутеры
    await init_db_tables(db_pool)
    register_handlers(dp)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
