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

from config import BOT_TOKEN, BOT_WALLET_ADDRESS, DB_NAME, MAX_DEPOSIT_STARS, MIN_DEPOSIT_STARS, MIN_DEPOSIT_TON, TON_API_KEY
from db import init_db, get_user, get_referral_stats, update_balance, update_ton_balance, set_free_case_time, reset_share_count, increment_share_count
from user_handlers import handlers_router
from admin_handlers import admin_router
from payments import payments_router, init_payment_db, register_payment_routes, api_stars_invoice
from utils import check_all_subscriptions
from crash_engine import init_crash_db, register_crash_routes
from battle_virtual import VirtualBattle

BASE_DIR = Path(__file__).resolve().parent
REQUIRED_CASE_CHANNEL = "eclipsedlf"
APP_NAME = "GIFTSMMS"
virtual_battle = VirtualBattle(DB_NAME)


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
    html = (BASE_DIR / "webapp" / "index.html").read_text(encoding="utf-8")
    marker = "</body>"
    if marker in html:
        injections = []
        if "/ton-payments.js" not in html:
            injections.append('<script src="/ton-payments.js"></script>')
        if "/battle-virtual.js" not in html:
            injections.append('<script src="/battle-virtual.js"></script>')
        if injections:
            html = html.replace(marker, "\n".join(injections) + "\n</body>")
    return web.Response(text=html, content_type="text/html")


async def handle_battle_js(request: web.Request):
    return web.FileResponse(BASE_DIR / "webapp" / "battle-virtual.js")


async def handle_ton_js(request: web.Request):
    return web.FileResponse(BASE_DIR / "webapp" / "ton-payments.js")


async def handle_ton_manifest(request: web.Request):
    return web.json_response({"url": str(request.url.with_path("/").with_query("")), "name": APP_NAME, "iconUrl": str(request.url.with_path("/icon-180.png").with_query(""))})


async def health(request: web.Request):
    return web.json_response({"status": "ok", "app": APP_NAME})


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
    return web.json_response({"ok": subscribed and available, "subscribed": subscribed, "available": available, "channel": REQUIRED_CASE_CHANNEL})


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
    return web.json_response({"count": count, "earned": earned, "link": f"https://t.me/{bot_info.username}?start=ref_{user_id}"})


async def api_deposit(request: web.Request):
    return await api_stars_invoice(request)


async def api_ton_deposit(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    if not BOT_WALLET_ADDRESS:
        return web.json_response({"ok": False, "message": "TON-кошелёк GIFTSMMS пока не настроен."})
    try:
        amount = float((await request.json()).get("amount", 0))
    except (TypeError, ValueError, json.JSONDecodeError):
        amount = 0
    if amount < MIN_DEPOSIT_TON:
        return web.json_response({"ok": False, "message": f"Минимум для TON: {MIN_DEPOSIT_TON:g} TON."})
    nonce = secrets.token_hex(6)
    comment = f"GIFTSMMS:{user_id}:{nonce}"
    tx_key = f"intent:{user_id}:{nonce}"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO ton_deposits (user_id,tx_hash,amount_ton,destination,status,created_at) VALUES (?,?,?,?,?,?)", (user_id, tx_key, amount, BOT_WALLET_ADDRESS, "pending", int(time.time())))
        await db.commit()
    nano = int(round(amount * 1_000_000_000))
    ton_uri = f"ton://transfer/{BOT_WALLET_ADDRESS}?amount={nano}&text={quote(comment)}"
    return web.json_response({"ok": True, "amount": amount, "comment": comment, "destination": BOT_WALLET_ADDRESS, "ton_uri": ton_uri, "message": "Отправьте TON на адрес GIFTSMMS, затем вставьте hash транзакции для проверки."})


async def api_ton_confirm(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    if not BOT_WALLET_ADDRESS or not TON_API_KEY:
        return web.json_response({"ok": False, "message": "TON-проверка не настроена: нужны BOT_WALLET_ADDRESS и TON_API_KEY."})
    try:
        body = await request.json()
        tx_hash = str(body.get("tx_hash", "")).strip().lower()
    except (TypeError, ValueError, json.JSONDecodeError):
        tx_hash = ""
    if len(tx_hash) < 40 or len(tx_hash) > 128:
        return web.json_response({"ok": False, "message": "Укажите корректный hash TON-транзакции."})
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT deposit_id,amount_ton,status FROM ton_deposits WHERE user_id=? AND status='pending' ORDER BY deposit_id DESC LIMIT 1", (user_id,)) as cursor:
            intent = await cursor.fetchone()
    if not intent:
        return web.json_response({"ok": False, "message": "Сначала создайте заявку на TON-пополнение."})
    headers = {"Authorization": f"Bearer {TON_API_KEY}"}
    try:
        async with ClientSession() as session:
            async with session.get(f"https://tonapi.io/v2/blockchain/transactions/{tx_hash}", headers=headers, timeout=12) as response:
                if response.status != 200:
                    return web.json_response({"ok": False, "message": "TON-транзакция пока не найдена. Проверьте hash через несколько секунд."})
                tx = await response.json()
    except Exception:
        return web.json_response({"ok": False, "message": "Не удалось проверить TON-транзакцию сейчас."})
    in_msg = tx.get("in_msg") or {}
    destination = str((in_msg.get("destination") or {}).get("address") or in_msg.get("destination") or "")
    source = str((in_msg.get("source") or {}).get("address") or in_msg.get("source") or "")
    value_nano = int(in_msg.get("value") or 0)
    message = str(in_msg.get("message") or "")
    decoded = in_msg.get("decoded_body") or {}
    if isinstance(decoded, dict):
        message = message or str(decoded.get("comment") or decoded.get("text") or "")
    expected_amount = float(intent[1])
    expected_nano = int(round(expected_amount * 1_000_000_000))
    expected_prefix = f"GIFTSMMS:{user_id}:"
    if destination and destination != BOT_WALLET_ADDRESS:
        return web.json_response({"ok": False, "message": "Эта транзакция отправлена не на кошелёк GIFTSMMS."})
    if value_nano < expected_nano or not message.startswith(expected_prefix):
        return web.json_response({"ok": False, "message": "Транзакция найдена, но сумма или комментарий не совпадают с заявкой."})
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT status FROM ton_deposits WHERE tx_hash=?", (tx_hash,)) as cursor:
            existing = await cursor.fetchone()
        if existing and existing[0] == "confirmed":
            return web.json_response({"ok": False, "message": "Эта транзакция уже была обработана."})
        await db.execute("UPDATE ton_deposits SET tx_hash=?, source_address=?, status='confirmed', confirmed_at=? WHERE deposit_id=? AND status='pending'", (tx_hash, source or None, int(time.time()), intent[0]))
        await db.commit()
    await update_ton_balance(user_id, expected_amount)
    return web.json_response({"ok": True, "credited_ton": expected_amount, "profile": await get_user(user_id)})


async def api_check_deposit(request: web.Request):
    return await api_ton_confirm(request)


async def api_public_battle(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    return web.json_response(await virtual_battle.snapshot(user_id))


async def api_public_battle_join(request: web.Request):
    user_id, _ = validate_webapp_user(request)
    try:
        body = await request.json()
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError, json.JSONDecodeError):
        return web.json_response({"ok": False, "message": "Некорректные данные."})
    return web.json_response(await virtual_battle.join(user_id, amount))


async def main():
    logging.info("Starting %s...", APP_NAME)
    await init_db()
    await init_payment_db()
    await init_crash_db(DB_NAME)
    await virtual_battle.init()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(handlers_router)
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", handle_index)
    app.router.add_get("/battle-virtual.js", handle_battle_js)
    app.router.add_get("/ton-payments.js", handle_ton_js)
    app.router.add_get("/health", health)
    app.router.add_get("/tonconnect-manifest.json", handle_ton_manifest)
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/share", api_share)
    app.router.add_get("/api/case-access", api_case_access)
    app.router.add_post("/api/free-case", api_free_case)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_post("/api/deposit", api_deposit)
    app.router.add_post("/api/ton/deposit", api_ton_deposit)
    app.router.add_post("/api/ton/confirm", api_ton_confirm)
    app.router.add_post("/api/deposit/check", api_check_deposit)
    app.router.add_get("/api/public-battle", api_public_battle)
    app.router.add_post("/api/public-battle/join", api_public_battle_join)
    register_payment_routes(app)
    register_crash_routes(app, DB_NAME, validate_webapp_user)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info("GIFTSMMS web server started on 0.0.0.0:%s", port)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("GIFTSMMS bot started")
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
