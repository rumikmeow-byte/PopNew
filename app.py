import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError
from config import settings
from database.db import init_db
from handlers.start import router as start_router
from handlers.balance import router as balance_router
from handlers.referrals import router as referrals_router
from handlers.channel import router as channel_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

async def health(request: web.Request):
    return web.Response(text="ok")

async def run_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    await site.start()
    logger.info("Health server listening on 0.0.0.0:%s", settings.port)
    return runner

async def main():
    runner = await run_health_server()

    # A second Render service may point at this same repository. Keep that
    # service healthy without starting a second Telegram polling session.
    if os.getenv("DISABLE_BOT_POLLING", "").strip().lower() in {"1", "true", "yes", "on"}:
        logger.info("Bot polling disabled by DISABLE_BOT_POLLING")
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
        return

    token = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        await runner.cleanup()
        raise RuntimeError("BOT_TOKEN is not configured in the environment")

    await init_db()
    bot = Bot(token)
    dp = Dispatcher()
    dp.include_routers(start_router, channel_router, referrals_router, balance_router)
    try:
        me = await bot.get_me()
        logger.info("Telegram bot authenticated as @%s (id=%s)", me.username, me.id)
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        logger.exception("BOT_TOKEN is invalid or revoked")
        raise
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
