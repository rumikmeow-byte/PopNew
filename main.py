import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import init_db
from user_handlers import handlers_router
from admin_handlers import admin_router

# Обработчик для index.html
async def handle_index(request):
    return web.FileResponse('webapp/index.html')

async def main():
    # Инициализация базы данных (создание таблиц)
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(handlers_router)
    dp.include_router(admin_router)

    await bot.delete_webhook(drop_pending_updates=True)

    # Запуск веб-сервера для Render
    app = web.Application()
    app.router.add_get('/', handle_index)
    port = int(os.environ.get('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)

    # Запускаем polling и веб-сервер одновременно
    await asyncio.gather(
        site.start(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
