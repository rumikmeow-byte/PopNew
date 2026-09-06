import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, quote

import aiosqlite
from aiohttp import ClientSession, web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, BOT_WALLET_ADDRESS, DB_NAME, MIN_DEPOSIT_TON, TON_API_KEY
from db import get_referral_stats, get_user, increment_share_count, init_db, reset_share_count, set_free_case_time, update_balance, update_ton_balance
from user_handlers import handlers_router
from miniapp_commands import router as miniapp_commands_router
from admin_handlers import admin_router
from payments import api_stars_invoice, init_payment_db, payments_router, register_payment_routes
from utils import check_all_subscriptions
from crash_engine import init_crash_db, register_crash_routes
from battle_virtual import VirtualBattle
from miniapp_features import MiniAppFeatures

BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "GIFTSMMS"
REQUIRED_CASE_CHANNEL = "eclipsedlf"
NEWS_CHANNEL = "@Eclipsedlf"
SUPPORT_USERNAME = "@Eclipsed_consult"
virtual_battle = VirtualBattle(DB_NAME)


def validate_webapp_user(request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise web.HTTPUnauthorized(text="Telegram initData is required")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", None)
    auth_date = pairs.get("auth_date")
    if not received or not auth_date:
        raise web.HTTPUnauthorized(text="Invalid Telegram initData")
    try:
        if int(time.time()) - int(auth_date) > 86400:
            raise web.HTTPUnauthorized(text="Telegram session expired")
    except ValueError:
        raise web.HTTPUnauthorized(text="Invalid auth_date")
    check = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received):
        raise web.HTTPUnauthorized(text="Invalid Telegram signature")
    try:
        user = json.loads(pairs["user"])
        return int(user["id"]), user
    except (ValueError, KeyError, json.JSONDecodeError):
        raise web.HTTPUnauthorized(text="Invalid Telegram user")


async def handle_index(request):
    html = (BASE_DIR / "webapp" / "index.html").read_text(encoding="utf-8")
    injections = []
    for src in ("/ton-payments.js", "/battle-virtual.js", "/cleanup.js"):
        if src not in html:
            injections.append(f'<script src="{src}"></script>')
    if injections:
        html = html.replace("</body>", "\n".join(injections) + "\n</body>")
    return web.Response(text=html, content_type="text/html")


def file_handler(name):
    async def handler(request):
        return web.FileResponse(BASE_DIR / "webapp" / name)
    return handler


async def health(request):
    return web.json_response({"status": "ok", "app": APP_NAME})


async def api_me(request):
    uid, telegram_user = validate_webapp_user(request)
    user = await get_user(uid)
    ref_count, ref_earned = await get_referral_stats(uid)
    return web.json_response({"user": telegram_user, "profile": user, "ref_count": ref_count, "ref_earned": ref_earned})


async def api_share(request):
    uid, _ = validate_webapp_user(request)
    user = await get_user(uid)
    if user["shared_count"] < 2:
        await increment_share_count(uid)
    return web.json_response({"ok": True, "shared_count": (await get_user(uid))["shared_count"]})


async def case_subscription_ok(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{REQUIRED_CASE_CHANNEL}", user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def api_case_access(request):
    uid, _ = validate_webapp_user(request)
    user = await get_user(uid)
    subscribed = await case_subscription_ok(request.app["bot"], uid)
    available = int(time.time()) - user["free_case_time"] >= 86400
    return web.json_response({"ok": subscribed and available, "subscribed": subscribed, "available": available, "channel": REQUIRED_CASE_CHANNEL})


async def api_free_case(request):
    uid, _ = validate_webapp_user(request)
    user = await get_user(uid)
    now = int(time.time())
    if now - user["free_case_time"] < 86400:
        return web.json_response({"ok": False, "message": "Бесплатный кейс будет доступен через 24 часа."})
    if not await case_subscription_ok(request.app["bot"], uid):
        return web.json_response({"ok": False, "message": "Подпишитесь на @eclipsedlf."})
    if not await check_all_subscriptions(request.app["bot"], uid):
        return web.json_response({"ok": False, "message": "Сначала подпишитесь на обязательные каналы."})
    if user["shared_count"] < 2:
        return web.json_response({"ok": False, "message": f"Поделитесь ссылкой 2 раза. Прогресс: {user['shared_count']}/2", "need_share": True})
    reward = secrets.choice([1, 5, 10])
    await update_balance(uid, reward)
    await set_free_case_time(uid, now)
    await reset_share_count(uid)
    return web.json_response({"ok": True, "reward": reward, "profile": await get_user(uid)})


async def api_referrals(request):
    uid, _ = validate_webapp_user(request)
    count, earned = await get_referral_stats(uid)
    bot = await request.app["bot"].get_me()
    return web.json_response({"count": count, "earned": earned, "link": f"https://t.me/{bot.username}?start=ref_{uid}"})


async def api_deposit(request):
    return await api_stars_invoice(request)


async def api_ton_deposit(request):
    uid, _ = validate_webapp_user(request)
    if not BOT_WALLET_ADDRESS:
        return web.json_response({"ok": False, "message": "TON-кошелёк GIFTSMMS пока не настроен."})
    try:
        amount = float((await request.json()).get("amount", 0))
    except Exception:
        amount = 0
    if amount < MIN_DEPOSIT_TON:
        return web.json_response({"ok": False, "message": f"Минимум для TON: {MIN_DEPOSIT_TON:g} TON."})
    nonce = secrets.token_hex(6)
    comment = f"GIFTSMMS:{uid}:{nonce}"
    intent_hash = f"intent:{uid}:{nonce}"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO ton_deposits(user_id,tx_hash,amount_ton,destination,status,created_at) VALUES(?,?,?,?,?,?)", (uid, intent_hash, amount, BOT_WALLET_ADDRESS, "pending", int(time.time())))
        await db.commit()
    uri = f"ton://transfer/{BOT_WALLET_ADDRESS}?amount={int(amount * 1e9)}&text={quote(comment)}"
    return web.json_response({"ok": True, "amount": amount, "comment": comment, "destination": BOT_WALLET_ADDRESS, "ton_uri": uri})


async def api_ton_confirm(request):
    uid, _ = validate_webapp_user(request)
    if not BOT_WALLET_ADDRESS or not TON_API_KEY:
        return web.json_response({"ok": False, "message": "TON-проверка не настроена."})
    try:
        tx_hash = str((await request.json()).get("tx_hash", "")).strip().lower()
    except Exception:
        tx_hash = ""
    if len(tx_hash) < 40:
        return web.json_response({"ok": False, "message": "Укажите корректный hash TON-транзакции."})
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT deposit_id,amount_ton FROM ton_deposits WHERE user_id=? AND status='pending' ORDER BY deposit_id DESC LIMIT 1", (uid,)) as cursor:
            intent = await cursor.fetchone()
        async with db.execute("SELECT 1 FROM ton_deposits WHERE tx_hash=? AND status='confirmed' LIMIT 1", (tx_hash,)) as cursor:
            already_used = await cursor.fetchone()
    if already_used:
        return web.json_response({"ok": False, "message": "Эта TON-транзакция уже была зачислена."})
    if not intent:
        return web.json_response({"ok": False, "message": "Сначала создайте заявку на TON-пополнение."})
    try:
        async with ClientSession() as session:
            async with session.get(f"https://tonapi.io/v2/blockchain/transactions/{tx_hash}", headers={"Authorization": f"Bearer {TON_API_KEY}"}, timeout=12) as response:
                if response.status != 200:
                    return web.json_response({"ok": False, "message": "TON-транзакция пока не найдена."})
                tx = await response.json()
    except Exception:
        return web.json_response({"ok": False, "message": "Не удалось проверить TON-транзакцию сейчас."})
    msg = tx.get("in_msg") or {}
    destination_data = msg.get("destination")
    destination = str(destination_data.get("address") or "") if isinstance(destination_data, dict) else str(destination_data or "")
    decoded = msg.get("decoded_body") or {}
    text = str(msg.get("message") or decoded.get("comment") or decoded.get("text") or "")
    value = int(msg.get("value") or 0)
    expected = float(intent[1])
    if ((destination and destination != BOT_WALLET_ADDRESS) or value < int(expected * 1e9) or not text.startswith(f"GIFTSMMS:{uid}:")):
        return web.json_response({"ok": False, "message": "Сумма, адрес или комментарий не совпадают с заявкой."})
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE ton_deposits SET tx_hash=?,status='confirmed',confirmed_at=? WHERE deposit_id=? AND status='pending'", (tx_hash, int(time.time()), intent[0]))
        await db.commit()
    await update_ton_balance(uid, expected)
    return web.json_response({"ok": True, "credited_ton": expected, "profile": await get_user(uid)})


async def api_public_battle(request):
    uid, _ = validate_webapp_user(request)
    return web.json_response(await virtual_battle.snapshot(uid))


async def api_public_battle_join(request):
    uid, _ = validate_webapp_user(request)
    try:
        amount = int((await request.json()).get("amount", 0))
    except Exception:
        return web.json_response({"ok": False, "message": "Некорректная сумма"})
    return web.json_response(await virtual_battle.join(uid, amount))


async def main():
    await init_db()
    await init_payment_db()
    await init_crash_db(DB_NAME)
    await virtual_battle.init()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    features = MiniAppFeatures(DB_NAME, bot)
    await features.init()
    dp = Dispatcher()
    dp.include_router(handlers_router)
    dp.include_router(miniapp_commands_router)
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", health)
    for asset in ("battle-virtual.js", "ton-payments.js", "animations.css", "giftsmms-logo.svg", "cleanup.js"):
        app.router.add_get(f"/{asset}", file_handler(asset))
    async def ton_manifest(request):
        base = str(request.url.with_path("/").with_query(""))
        return web.json_response({"url": base, "name": APP_NAME, "iconUrl": f"{base}giftsmms-logo.svg"})
    app.router.add_get("/tonconnect-manifest.json", ton_manifest)
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/share", api_share)
    app.router.add_get("/api/case-access", api_case_access)
    app.router.add_post("/api/free-case", api_free_case)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_post("/api/deposit", api_deposit)
    app.router.add_post("/api/ton/deposit", api_ton_deposit)
    app.router.add_post("/api/ton/confirm", api_ton_confirm)
    app.router.add_post("/api/deposit/check", api_ton_confirm)
    app.router.add_get("/api/public-battle", api_public_battle)
    app.router.add_post("/api/public-battle/join", api_public_battle_join)
    await features.routes(app, validate_webapp_user)
    register_payment_routes(app)
    register_crash_routes(app, DB_NAME, validate_webapp_user)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("GIFTSMMS server started on %s | news=%s | support=%s", port, NEWS_CHANNEL, SUPPORT_USERNAME)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s | %(levelname)s | %(message)s")
    asyncio.run(main())
