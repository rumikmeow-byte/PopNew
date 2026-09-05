import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
# Импортируйте ваши роутеры/хэндлеры (пример:
# from user_handlers import router as user_router
# from admin_handlers import router as admin_router

async def main():
    # Инициализация бота с токеном из config.py
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Регистрация роутеров
    # dp.include_router(user_router)
    # dp.include_router(admin_router)

    # Пропуск старых апдейтов и запуск поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
