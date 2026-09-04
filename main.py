import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web

# Импортируем инициализацию БД и роутеры из gift_modules.py
from gift_modules import register_handlers, init_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Обработчик запросов к веб-серверу (отдает web/index.html для Telegram Mini App)
async def handle_index(request):
    return web.FileResponse('./web/index.html')


async def main():
    if not BOT_TOKEN:
        raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

    # 1. Инициализация базы данных SQLite
    logging.info("Инициализация базы данных...")
    await init_db()

    # 2. Регистрация обработчиков сообщений из gift_modules.py
    register_handlers(dp)

    # 3. Настройка и запуск веб-сервера aiohttp для Mini App
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_static('/static/', path='./web', name='static')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    logging.info(f"Веб-сервер Mini App успешно запущен на порту {PORT}")

    # 4. Запуск поллинга бота
    logging.info("Запуск Telegram-бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
