import asyncio
import logging
import os
import sys
from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from db import init_db
from user_handlers import handlers_router
from admin_handlers import admin_router

BASE_DIR = Path(__file__).resolve().parent


async def handle_index(request: web.Request):
    index_path = BASE_DIR / "webapp" / "index.html"

    if not index_path.exists():
        return web.Response(
            text="PopNew is running",
            content_type="text/plain",
        )

    return web.FileResponse(index_path)


async def health(request: web.Request):
    return web.json_response({"status": "ok"})


async def main():
    logging.info("Starting PopNew...")

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        ),
    )

    dp = Dispatcher()

    dp.include_router(handlers_router)
    dp.include_router(admin_router)

    app = web.Application()

    app.router.add_get("/", handle_index)
    app.router.add_get("/health", health)

    port = int(os.getenv("PORT", "10000"))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=port,
    )

    await site.start()

    logging.info(
        "Web server started on 0.0.0.0:%s",
        port,
    )

    try:
        await bot.delete_webhook(
            drop_pending_updates=True
        )

        logging.info("Telegram bot started")

        await dp.start_polling(bot)

    except asyncio.CancelledError:
        logging.info("Bot stopping...")
        raise

    finally:
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
