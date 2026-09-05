import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import (
    BOT_TOKEN,
    BOT_WALLET_ADDRESS,
    DB_NAME,
    MAX_DEPOSIT_STARS,
    MIN_DEPOSIT_STARS,
    MIN_DEPOSIT_TON,
    TON_TO_STARS_RATE,
)
from db import (
    init_db,
    get_user,
    get_referral_stats,
    update_balance,
    set_free_case_time,
    reset_share_count,
    increment_share_count,
    create_battle,
    add_player_to_battle,
    get_battle_info,
    get_active_battles,
    get_battle_players,
    get_battle_snapshot,
    start_ready_battles,
    resolve_finished_battles,
)
from user_handlers import handlers_router
from admin_handlers import admin_router
from payments import payments_router, init_payment_db, register_payment_routes, api_stars_invoice
from utils import check_all_subscriptions
from crash_engine import init_crash_db, register_crash_routes

BASE_DIR = Path(__file__).resolve().parent
REQUIRED_CASE_CHANNEL = "eclipsedlf"
APP_NAME = "GIFTSMMS"


def validate_webapp_user(request: web.Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise web.HTTPUnauthorized(text="Telegram initData is required")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    auth_date = pairs.get("auth_date")
    if not received_hash or not auth_date:
        raise web.HTTPUnauthorized(text="Invalid Telegram initData")
    try:
        if int(time.time()) - int(auth_date) > 86400:
            raise web.HTTPUnauthorized(text="Telegram session expired")
    except ValueError:
        raise web.HTTPUnauthorized(text="Invalid auth_date")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise web.HTTPUnauthorized(text="Invalid Telegram signature")
    user_raw = pairs.get("user")
    if not user_raw:
        raise web.HTTPUnauthorized(text="Telegram user is missing")
    try:
        user = json.loads(user_raw)
        return int(user["id"]), user
    except (ValueError, KeyError, json.JSONDecodeError):
        raise web.HTTPUnauthorized(text="Invalid Telegram user")


async def handle_index(request: web.Request):
    return web.FileResponse(BASE_DIR / "webapp" / "index.html")


async def handle_ton_manifest(request: web.Request):
    return web.json_response({
        "url": str(request.url.with_path("/").with_query("")),
        "name": APP_NAME,
        "iconUrl": str(request.url.with_path("/icon-180.png").with_query("")),
    })


async def health(request: web.Request):
    return web.json_response({"status": "ok", "app": APP_NAME})


async def api_me(request: web.Request):
    user_id, tg_user = validate_webapp_user(request)
    user = await get_user(user_id)
    ref_count, ref_earned = await get_referral_stats(user_id)
    return web.json_response({
        "user": tg_user,
        "profile": user,
        "ref_count": ref_count,
        "ref_earned": ref_earned,
    })


async def api_share(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    user = await get_user(user_id)
    if user["shared_count"] >= 2:
        return web.json_response({"ok": True, "shared_count": 2})
    await increment_share_count(user_id)
    user = await get_user(user_id)
    return web.json_response({"ok": True, "shared_count": user["shared_count"]})


async def case_subscription_ok(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{REQUIRED_CASE_CHANNEL}", user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def api_case_access(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    subscribed = await case_subscription_ok(request.app["bot"], user_id)
    user = await get_user(user_id)
    available = int(time.time()) - user["free_case_time"] >= 86400
    return web.json_response({
        "ok": subscribed and available,
        "subscribed": subscribed,
        "available": available,
        "channel": REQUIRED_CASE_CHANNEL,
    })


async def api_free_case(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    user = await get_user(user_id)
    now = int(time.time())
    if now - user["free_case_time"] < 86400:
        return web.json_response({"ok": False, "message": "Бесплатный кейс будет доступен через 24 часа."})
    if not await case_subscription_ok(request.app["bot"], user_id):
        return web.json_response({"ok": False, "message": "Подпишитесь на @eclipsedlf и нажмите «Проверить подписку»."})
    if not await check_all_subscriptions(request.app["bot"], user_id):
        return web.json_response({"ok": False, "message": "Сначала подпишитесь на обязательные каналы."})
    if user["shared_count"] < 2:
        return web.json_response({
            "ok": False,
            "message": f"Сначала поделитесь ссылкой 2 раза. Прогресс: {user['shared_count']}/2",
            "need_share": True,
        })
    import random
    reward = random.choice([1, 5, 10])
    await update_balance(user_id, reward)
    await set_free_case_time(user_id, now)
    await reset_share_count(user_id)
    return web.json_response({"ok": True, "reward": reward, "profile": await get_user(user_id)})


async def api_referrals(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    count, earned = await get_referral_stats(user_id)
    bot_info = await request.app["bot"].get_me()
    return web.json_response({
        "count": count,
        "earned": earned,
        "link": f"https://t.me/{bot_info.username}?start=ref_{user_id}",
    })


async def api_deposit(request: web.Request):
    # Compatibility alias: in Telegram Mini Apps, digital services are paid with Stars.
    return await api_stars_invoice(request)


async def api_check_deposit(request: web.Request):
    validate_webapp_user(request)
    return web.json_response({
        "ok": False,
        "message": "Проверка TON-депозита отключена. Используйте Telegram Stars для пополнения GIFTSMMS.",
    })


async def api_battles(request: web.Request):
    validate_webapp_user(request)
    await start_ready_battles(start_delay=3)
    await resolve_finished_battles(round_seconds=8)
    rows = await get_active_battles()
    battles = []
    for r in rows:
        players = await get_battle_players(r[0])
        battles.append({
            "battle_id": r[0],
            "creator_id": r[1],
            "currency": r[2],
            "bank_stars": r[3],
            "bank_ton": r[4],
            "hash": r[5],
            "max_players": r[6],
            "status": r[7],
            "winner_id": r[8],
            "created_at": r[9],
            "started_at": r[10],
            "ended_at": r[11],
            "players_count": len(players),
        })
    return web.json_response({"battles": battles})


async def api_battle(request: web.Request):
    validate_webapp_user(request)
    try:
        battle_id = int(request.match_info["battle_id"])
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="Некорректный battle_id")
    await start_ready_battles(start_delay=3)
    await resolve_finished_battles(round_seconds=8)
    snapshot = await get_battle_snapshot(battle_id)
    if not snapshot:
        raise web.HTTPNotFound(text="Батл не найден")
    return web.json_response(snapshot)


async def api_create_battle(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    body = await request.json()
    currency = str(body.get("currency", "stars")).lower()
    try:
        max_players = max(2, min(10, int(body.get("max_players", 10))))
    except (TypeError, ValueError):
        max_players = 10
    # Real-value game currency is Stars; TON remains a wallet-only integration.
    if currency != "stars":
        return web.json_response({"ok": False, "message": "GIFTSMMS battles use Telegram Stars."})
    battle_id = await create_battle(user_id, currency, max_players)
    return web.json_response({"ok": True, "battle_id": battle_id})


async def api_join_battle(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    body = await request.json()
    try:
        battle_id = int(body.get("battle_id"))
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "message": "Некорректные данные."})
    if amount < MIN_DEPOSIT_STARS or amount > MAX_DEPOSIT_STARS:
        return web.json_response({"ok": False, "message": f"Ставка: от {MIN_DEPOSIT_STARS} до {MAX_DEPOSIT_STARS} ⭐."})
    battle = await get_battle_info(battle_id)
    if not battle or battle["currency"] != "stars":
        return web.json_response({"ok": False, "message": "Батл не найден."})
    user = await get_user(user_id)
    if user["balance"] < amount:
        return web.json_response({"ok": False, "message": "Недостаточно ⭐."})
    await update_balance(user_id, -amount)
    ok, message = await add_player_to_battle(battle_id, user_id, bet_stars=amount)
    if not ok:
        await update_balance(user_id, amount)
    return web.json_response({
        "ok": ok,
        "message": message,
        "battle": await get_battle_snapshot(battle_id) if ok else None,
    })


async def battle_engine_loop():
    logging.info("GIFTSMMS battle engine started")
    while True:
        try:
            await start_ready_battles(start_delay=3)
            await resolve_finished_battles(round_seconds=8)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.exception("Battle engine tick failed")
        await asyncio.sleep(0.5)


async def main():
    logging.info("Starting %s...", APP_NAME)
    await init_db()
    await init_payment_db()
    await init_crash_db(DB_NAME)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(handlers_router)
    dp.include_router(admin_router)
    dp.include_router(payments_router)

    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", health)
    app.router.add_get("/tonconnect-manifest.json", handle_ton_manifest)
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/share", api_share)
    app.router.add_get("/api/case-access", api_case_access)
    app.router.add_post("/api/free-case", api_free_case)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_post("/api/deposit", api_deposit)
    app.router.add_post("/api/deposit/check", api_check_deposit)
    app.router.add_get("/api/battles", api_battles)
    app.router.add_get("/api/battles/{battle_id}", api_battle)
    app.router.add_post("/api/battles", api_create_battle)
    app.router.add_post("/api/battles/join", api_join_battle)
    register_payment_routes(app)
    register_crash_routes(app, DB_NAME, validate_webapp_user)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    engine_task = asyncio.create_task(battle_engine_loop())
    logging.info("GIFTSMMS web server started on 0.0.0.0:%s", port)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("GIFTSMMS bot started")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logging.info("Bot stopping...")
        raise
    finally:
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
