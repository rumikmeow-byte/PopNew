import os
import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher
from aiohttp import web
from gift_modules import register_handlers, init_db_tables

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 8080))  # Render автоматически передаёт порт

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обработчик отдачи главной страницы WebApp
async def handle_index(request):
    return web.FileResponse('./web/index.html')

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан!")

    # Подключение к базе данных
    db_pool = await asyncpg.create_pool(dsn=DATABASE_URL)
    await init_db_tables(db_pool)

    dp["db_pool"] = db_pool
    register_handlers(dp)

    # Настройка и запуск Web-сервера для Mini App
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_static('/static/', path='./web', name='static')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    logging.info(f"Веб-сервер Mini App запущен на порту {PORT}")

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
