import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import settings
from database.db import init_db
from handlers.start import router as start_router
from handlers.balance import router as balance_router
from handlers.game import router as game_router
from handlers.payments import router as payments_router
from handlers.support import router as support_router

logging.basicConfig(level=logging.INFO)

async def health(request):
    return web.Response(text="ok")

async def run_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    await site.start()
    return runner

async def main():
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")
    await init_db()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_routers(start_router, balance_router, game_router, payments_router, support_router)
    runner = await run_health_server()
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
