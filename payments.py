import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web
from aiogram import F, Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery

from config import BOT_TOKEN, MAX_DEPOSIT_STARS, DB_NAME
from db import update_balance

payments_router = Router()


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
        return int(user["id"])
    except (ValueError, KeyError, json.JSONDecodeError):
        raise web.HTTPUnauthorized(text="Invalid Telegram user")


async def init_payment_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_records (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_key TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                stars_amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                charge_id TEXT,
                created_at INTEGER NOT NULL,
                confirmed_at INTEGER DEFAULT NULL
            )
        """)
        await db.commit()


async def record_payment(payment_key, user_id, method, stars_amount, charge_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            """INSERT OR IGNORE INTO payment_records
               (payment_key,user_id,method,stars_amount,status,charge_id,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (payment_key, user_id, method, stars_amount, "pending", charge_id, int(time.time())),
        )
        await db.commit()
        return cur.rowcount == 1


async def confirm_payment(payment_key, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            """UPDATE payment_records
               SET status='confirmed', confirmed_at=?
               WHERE payment_key=? AND user_id=? AND status='pending'""",
            (int(time.time()), payment_key, user_id),
        )
        await db.commit()
        return cur.rowcount == 1


async def payment_is_confirmed(payment_key, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT status FROM payment_records WHERE payment_key=? AND user_id=?",
            (payment_key, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return bool(row and row[0] == "confirmed")


async def record_ton_payment(user_id, stars_amount, comment):
    return await record_payment(f"ton:{comment}", user_id, "ton", stars_amount)


async def confirm_ton_payment(user_id, comment):
    return await confirm_payment(f"ton:{comment}", user_id)


async def api_stars_invoice(request: web.Request):
    user_id = validate_webapp_user(request)
    body = await request.json()
    try:
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0 or amount > MAX_DEPOSIT_STARS:
        return web.json_response({"ok": False, "message": f"Сумма должна быть от 1 до {MAX_DEPOSIT_STARS} ⭐."})

    nonce = int(time.time() * 1000)
    payload = f"stars_deposit:{user_id}:{amount}:{nonce}"
    await record_payment(payload, user_id, "stars", amount)

    bot = request.app["bot"]
    invoice_link = await bot.create_invoice_link(
        title=f"Пополнение {amount} ⭐",
        description=f"Пополнение внутреннего баланса PopNew на {amount} Telegram Stars.",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)],
        provider_token="",
    )
    return web.json_response({"ok": True, "amount": amount, "invoice_link": invoice_link})


@payments_router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    payload = query.invoice_payload or ""
    if not payload.startswith("stars_deposit:"):
        await query.answer(ok=False, error_message="Неизвестный платёж.")
        return
    try:
        _, user_id, amount, _ = payload.split(":")
        if int(user_id) != query.from_user.id or int(amount) <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await query.answer(ok=False, error_message="Некорректный платёж.")
        return
    await query.answer(ok=True)


@payments_router.message(F.successful_payment)
async def successful_stars_payment(message: types.Message):
    payment = message.successful_payment
    if not payment or payment.currency != "XTR":
        return
    payload = payment.invoice_payload or ""
    if not payload.startswith("stars_deposit:"):
        return
    try:
        _, user_id, amount, _ = payload.split(":")
        user_id = int(user_id)
        amount = int(amount)
    except (ValueError, TypeError):
        return
    if message.from_user.id != user_id or payment.total_amount != amount:
        return

    charge_id = payment.telegram_payment_charge_id
    key = f"stars_charge:{charge_id}"
    inserted = await record_payment(key, user_id, "stars", amount, charge_id=charge_id)
    if inserted:
        await update_balance(user_id, amount)
        await confirm_payment(key, user_id)
        try:
            await message.answer(f"✅ Оплата получена. На баланс зачислено {amount} ⭐.")
        except Exception:
            pass


def register_payment_routes(app: web.Application):
    app.router.add_post("/api/stars/invoice", api_stars_invoice)
