import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, BOT_WALLET_ADDRESS, MAX_DEPOSIT_STARS, TON_TO_STARS_RATE
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
)
from user_handlers import handlers_router
from admin_handlers import admin_router
from utils import check_all_subscriptions, check_transaction

BASE_DIR = Path(__file__).resolve().parent


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
    index_path = BASE_DIR / "webapp" / "index.html"
    return web.FileResponse(index_path)


async def health(request: web.Request):
    return web.json_response({"status": "ok"})


async def api_me(request: web.Request):
    user_id, tg_user = validate_webapp_user(request)
    user = await get_user(user_id)
    ref_count, ref_earned = await get_referral_stats(user_id)
    return web.json_response({"user": tg_user, "profile": user, "ref_count": ref_count, "ref_earned": ref_earned})


async def api_share(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    user = await get_user(user_id)
    if user["shared_count"] >= 2:
        return web.json_response({"ok": True, "shared_count": 2})
    await increment_share_count(user_id)
    user = await get_user(user_id)
    return web.json_response({"ok": True, "shared_count": user["shared_count"]})


async def api_free_case(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    user = await get_user(user_id)
    now = int(time.time())
    if now - user["free_case_time"] < 86400:
        return web.json_response({"ok": False, "message": "Бесплатный кейс будет доступен через 24 часа."})
    if not await check_all_subscriptions(request.app["bot"], user_id):
        return web.json_response({"ok": False, "message": "Сначала подпишитесь на обязательные каналы."})
    if user["shared_count"] < 2:
        return web.json_response({"ok": False, "message": f"Сначала поделитесь ссылкой 2 раза. Прогресс: {user['shared_count']}/2", "need_share": True})

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
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    return web.json_response({"count": count, "earned": earned, "link": link})


async def api_deposit(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    body = await request.json()
    try:
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0 or amount > MAX_DEPOSIT_STARS:
        return web.json_response({"ok": False, "message": f"Сумма должна быть от 1 до {MAX_DEPOSIT_STARS} ⭐."})
    if not BOT_WALLET_ADDRESS or TON_TO_STARS_RATE <= 0:
        return web.json_response({"ok": False, "message": "Пополнение пока не настроено."})
    ton_amount = amount / TON_TO_STARS_RATE
    comment = f"dep_{user_id}_{amount}_{int(time.time())}"
    ton_link = f"ton://transfer/{BOT_WALLET_ADDRESS}?{urlencode({'amount': int(ton_amount * 1e9), 'text': comment})}"
    return web.json_response({"ok": True, "amount": amount, "ton": ton_amount, "comment": comment, "ton_link": ton_link})


async def api_check_deposit(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    body = await request.json()
    comment = str(body.get("comment", ""))
    try:
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if not comment.startswith(f"dep_{user_id}_") or amount <= 0:
        return web.json_response({"ok": False, "message": "Некорректный платёж."})
    ton_amount = amount / TON_TO_STARS_RATE
    if await check_transaction(comment, ton_amount):
        await update_balance(user_id, amount)
        return web.json_response({"ok": True, "message": f"Баланс пополнен на {amount} ⭐.", "profile": await get_user(user_id)})
    return web.json_response({"ok": False, "message": "Платёж пока не найден."})


async def api_battles(request: web.Request):
    validate_webapp_user(request)
    rows = await get_active_battles()
    battles = []
    for row in rows:
        battles.append({"battle_id": row[0], "creator_id": row[1], "currency": row[2], "bank_stars": row[3], "bank_ton": row[4], "hash": row[5], "max_players": row[6]})
    return web.json_response({"battles": battles})


async def api_create_battle(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    body = await request.json()
    currency = str(body.get("currency", "stars")).lower()
    try:
        max_players = max(2, min(10, int(body.get("max_players", 10))))
    except (TypeError, ValueError):
        max_players = 10
    if currency not in ("stars", "ton"):
        return web.json_response({"ok": False, "message": "Неверная валюта."})
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
    battle = await get_battle_info(battle_id)
    if not battle or amount <= 0:
        return web.json_response({"ok": False, "message": "Батл не найден или ставка неверна."})
    if battle["currency"] == "stars":
        user = await get_user(user_id)
        if user["balance"] < amount:
            return web.json_response({"ok": False, "message": "Недостаточно ⭐."})
        await update_balance(user_id, -amount)
        ok, message = await add_player_to_battle(battle_id, user_id, bet_stars=amount)
        if not ok:
            await update_balance(user_id, amount)
        return web.json_response({"ok": ok, "message": message})
    return web.json_response({"ok": False, "message": "TON-баттлы оформляются через раздел пополнения."})


async def main():
    logging.info("Starting PopNew...")
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(handlers_router)
    dp.include_router(admin_router)

    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", health)
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/share", api_share)
    app.router.add_post("/api/free-case", api_free_case)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_post("/api/deposit", api_deposit)
    app.router.add_post("/api/deposit/check", api_check_deposit)
    app.router.add_get("/api/battles", api_battles)
    app.router.add_post("/api/battles", api_create_battle)
    app.router.add_post("/api/battles/join", api_join_battle)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info("Web server started on 0.0.0.0:%s", port)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Telegram bot started")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logging.info("Bot stopping...")
        raise
    finally:
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
