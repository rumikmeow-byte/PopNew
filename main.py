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
from aiohttp import ClientSession, WSMsgType, web
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import BaseMiddleware

from config import ADMIN_ID, BOT_TOKEN, BOT_WALLET_ADDRESS, DB_NAME, MIN_DEPOSIT_TON, TON_API_KEY
from db import add_referral, get_referral_stats, get_user, increment_share_count, update_ton_balance, init_db
from user_handlers import handlers_router
from miniapp_commands import router as miniapp_commands_router
from admin_handlers import admin_router
from payments import api_stars_invoice, init_payment_db, payments_router, register_payment_routes
from crash_engine import init_crash_db, register_crash_routes, crash_state, place_crash_bet, cashout_crash_bet
from battle_virtual import VirtualBattle
from ton_battle import TonBattle
from miniapp_features import MiniAppFeatures

BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "GiftsEZZ"
REQUIRED_CASE_CHANNEL = "eclipsedlf"
NEWS_CHANNEL = "@Eclipsedlf"
SUPPORT_USERNAME = "@Eclipsed_consult"
FREE_CASE_DROPS = ((1.0, 80), (1.5, 18), (5.0, 2))
virtual_battle = VirtualBattle(DB_NAME)
ton_battle = TonBattle(DB_NAME)


async def subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{REQUIRED_CASE_CHANNEL}", user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


class SubscriptionGateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)
        if user.id == ADMIN_ID:
            return await handler(event, data)
        bot = data.get("bot")
        if await subscribed(bot, user.id):
            return await handler(event, data)

        if isinstance(event, types.Message) and event.text and event.text.startswith("/start"):
            await event.answer(
                "🔒 Чтобы пользоваться GiftsEZZ, сначала подпишитесь на @eclipsedlf.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/eclipsedlf")],
                    [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub_access")],
                ]),
            )
            return
        if isinstance(event, types.CallbackQuery) and event.data == "check_sub_access":
            if await subscribed(bot, user.id):
                await event.message.edit_text("✅ Подписка подтверждена. Нажмите /start ещё раз.")
                await event.answer("Готово")
            else:
                await event.answer("❌ Подписка пока не найдена.", show_alert=True)
            return
        if isinstance(event, types.CallbackQuery):
            await event.answer("🔒 Сначала подпишитесь на @eclipsedlf.", show_alert=True)
        else:
            await event.answer("🔒 Сначала подпишитесь на @eclipsedlf.")


async def require_webapp_subscription(request, uid: int):
    if uid == ADMIN_ID:
        return True
    if not await subscribed(request.app["bot"], uid):
        raise web.HTTPForbidden(text="Подпишитесь на @eclipsedlf")
    return True


def validate_webapp_user(request):
    init_data = request.headers.get("X-Telegram-Init-Data", "") or request.query.get("initData", "")
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
    for src in ("/ton-payments.js", "/battle-virtual.js", "/cleanup.js", "/ton-game.js", "/safe-ui.js"):
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


async def process_startapp_referral(request, uid: int):
    init_data = request.headers.get("X-Telegram-Init-Data", "") or request.query.get("initData", "")
    if not init_data:
        return
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    start_param = (pairs.get("start_param") or request.query.get("startapp") or "").strip()
    if not start_param.startswith("ref_"):
        return
    try:
        referrer_id = int(start_param.split("_", 1)[1])
    except (ValueError, IndexError):
        return
    if referrer_id == uid:
        return
    user = await get_user(uid)
    if user and int(user.get("ref_count", 0) or 0) == 0 and float(user.get("balance", 0) or 0) == 0:
        await add_referral(referrer_id, uid)


async def api_me(request):
    uid, telegram_user = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    await process_startapp_referral(request, uid)
    user = await get_user(uid)
    ref_count, ref_earned = await get_referral_stats(uid)
    return web.json_response({"user": telegram_user, "profile": user, "ref_count": ref_count, "ref_earned": ref_earned, "subscribed": True})


async def api_share(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    await increment_share_count(uid)
    return web.json_response({"ok": True, "shared_count": (await get_user(uid))["shared_count"]})


async def case_subscription_ok(bot, user_id):
    return await subscribed(bot, user_id)


async def api_case_access(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    user = await get_user(uid)
    ref_count, _ = await get_referral_stats(uid)
    available = int(time.time()) - int(user["free_case_time"] or 0) >= 86400
    return web.json_response({
        "ok": ref_count >= 3 and available,
        "subscribed": True,
        "referrals": ref_count,
        "need_referrals": max(0, 3 - ref_count),
        "available": available,
        "channel": REQUIRED_CASE_CHANNEL,
    })


def choose_free_case_drop():
    ticket = secrets.randbelow(100)
    cursor = 0
    for amount, weight in FREE_CASE_DROPS:
        cursor += weight
        if ticket < cursor:
            return amount
    return FREE_CASE_DROPS[-1][0]


async def api_free_case(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT balance,free_case_time FROM users WHERE user_id=?", (uid,)) as cur:
            user = await cur.fetchone()
        if not user:
            await db.execute("INSERT INTO users(user_id) VALUES(?)", (uid,))
            free_case_time = 0
        else:
            free_case_time = int(user[1] or 0)
        async with db.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=?", (uid,)) as cur:
            ref_count = int((await cur.fetchone())[0])
        if now - free_case_time < 86400:
            await db.rollback()
            return web.json_response({"ok": False, "message": "Бесплатный кейс будет доступен через 24 часа."})
        if ref_count < 3:
            await db.rollback()
            return web.json_response({"ok": False, "message": f"Пригласите ещё {3-ref_count} друзей.", "referrals": ref_count, "need_referrals": 3-ref_count})
        reward = choose_free_case_drop()
        await db.execute("UPDATE users SET balance=balance+?, free_case_time=? WHERE user_id=?", (reward, now, uid))
        await db.commit()
    return web.json_response({"ok": True, "reward": reward, "probabilities": {"1": 80, "1.5": 18, "5": 2}, "profile": await get_user(uid)})


async def api_referrals(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    count, earned = await get_referral_stats(uid)
    bot = await request.app["bot"].get_me()
    return web.json_response({"count": count, "earned": earned, "link": f"https://t.me/{bot.username}?startapp=ref_{uid}"})


async def api_deposit(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    return await api_stars_invoice(request)


async def api_ton_deposit(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    if not BOT_WALLET_ADDRESS:
        return web.json_response({"ok": False, "message": "TON-кошелёк GiftsEZZ пока не настроен."})
    try:
        amount = float((await request.json()).get("amount", 0))
    except Exception:
        amount = 0
    if amount < MIN_DEPOSIT_TON:
        return web.json_response({"ok": False, "message": f"Минимум для TON: {MIN_DEPOSIT_TON:g} TON."})
    nonce = secrets.token_hex(6)
    comment = f"GIFTSEZZ:{uid}:{nonce}"
    intent_hash = f"intent:{uid}:{nonce}"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO ton_deposits(user_id,tx_hash,amount_ton,destination,status,created_at) VALUES(?,?,?,?,?,?)", (uid, intent_hash, amount, BOT_WALLET_ADDRESS, "pending", int(time.time())))
        await db.commit()
    uri = f"ton://transfer/{BOT_WALLET_ADDRESS}?amount={int(amount * 1e9)}&text={quote(comment)}"
    return web.json_response({"ok": True, "amount": amount, "comment": comment, "destination": BOT_WALLET_ADDRESS, "ton_uri": uri})


async def api_ton_confirm(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
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
    if ((destination and destination != BOT_WALLET_ADDRESS) or value < int(expected * 1e9) or not text.startswith(f"GIFTSEZZ:{uid}:")):
        return web.json_response({"ok": False, "message": "Сумма, адрес или комментарий не совпадают с заявкой."})
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE ton_deposits SET tx_hash=?,status='confirmed',confirmed_at=? WHERE deposit_id=? AND status='pending'", (tx_hash, int(time.time()), intent[0]))
        await db.commit()
    await update_ton_balance(uid, expected)
    return web.json_response({"ok": True, "credited_ton": expected, "profile": await get_user(uid)})


async def api_public_battle(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    return web.json_response(await virtual_battle.snapshot(uid))


async def api_public_battle_join(request):
    uid, telegram_user = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    try:
        amount = int((await request.json()).get("amount", 0))
    except Exception:
        return web.json_response({"ok": False, "message": "Некорректная сумма"})
    display_name = telegram_user.get("username") or " ".join(x for x in [telegram_user.get("first_name"), telegram_user.get("last_name")] if x) or f"Игрок {uid}"
    return web.json_response(await virtual_battle.join(uid, amount, display_name))


async def api_ton_battle(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    return web.json_response({"ok": False, "message": "TON-ставки отключены. Используйте арену с виртуальными очками."})


async def api_ton_battle_join(request):
    uid, _ = validate_webapp_user(request)
    await require_webapp_subscription(request, uid)
    return web.json_response({"ok": False, "message": "TON-ставки отключены. Используйте виртуальные очки."})


async def api_ws(request):
    try:
        uid, telegram_user = validate_webapp_user(request)
        await require_webapp_subscription(request, uid)
    except web.HTTPException as exc:
        return exc
    display_name = telegram_user.get("username") or " ".join(x for x in [telegram_user.get("first_name"), telegram_user.get("last_name")] if x) or f"Игрок {uid}"
    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)
    try:
        while not ws.closed:
            payload = {
                "type": "state",
                "server_time": time.time(),
                "arena": await virtual_battle.snapshot(uid),
            }
            await ws.send_json(payload)
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                if msg.type == WSMsgType.TEXT:
                    try:
                        action = json.loads(msg.data)
                    except json.JSONDecodeError:
                        action = {}
                    kind = action.get("action")
                    if kind == "arena_bet":
                        result = await virtual_battle.join(uid, int(action.get("amount", 0)), display_name)
                        await ws.send_json({"type": "action", "action": kind, **result})
                    elif kind in ("crash_bet", "crash_cashout", "ton_bet"):
                        await ws.send_json({"type": "action", "action": kind, "ok": False, "message": "Реальные ставки отключены. Используйте виртуальные очки."})
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.ERROR):
                    break
            except asyncio.TimeoutError:
                continue
    finally:
        await ws.close()
    return ws


async def main():
    await init_db()
    await init_payment_db()
    await init_crash_db(DB_NAME)
    await virtual_battle.init()
    await ton_battle.init()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    features = MiniAppFeatures(DB_NAME, bot)
    await features.init()
    dp = Dispatcher()
    dp.message.middleware(SubscriptionGateMiddleware())
    dp.callback_query.middleware(SubscriptionGateMiddleware())
    dp.include_router(handlers_router)
    dp.include_router(miniapp_commands_router)
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", health)
    for asset in ("battle-virtual.js", "ton-payments.js", "ton-game.js", "animations.css", "giftsmms-logo.svg", "cleanup.js", "safe-ui.js"):
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
    app.router.add_get("/api/ton-battle", api_ton_battle)
    app.router.add_post("/api/ton-battle/join", api_ton_battle_join)
    app.router.add_get("/ws", api_ws)
    await features.routes(app, validate_webapp_user)
    register_payment_routes(app)
    register_crash_routes(app, DB_NAME, validate_webapp_user)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("%s server started on %s | news=%s | support=%s", APP_NAME, port, NEWS_CHANNEL, SUPPORT_USERNAME)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s | %(levelname)s | %(message)s")
    asyncio.run(main())
