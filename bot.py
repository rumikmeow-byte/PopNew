import os
import json
import asyncio
import logging

from aiosqlite import connect
from aiohttp import web, WSMsgType

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    LabeledPrice,
)

from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

TON_WALLET = os.getenv(
    "TON_WALLET",
    "UQA6OOWd_V_-asdDgsjiHK3OYTp-FjGihgFNxpSg__dHM1h8"
)

WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()
PORT = int(os.getenv("PORT", "8080"))

DB_NAME = "database.db"

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен")

if not WEBAPP_URL:
    logging.warning(
        "WEBAPP_URL не установлен. "
        "Кнопка Web App не будет работать правильно."
    )


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp")
INDEX_FILE = os.path.join(WEBAPP_DIR, "index.html")


# ============================================================
# DATABASE
# ============================================================

async def init_db():
    async with connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                stars INTEGER DEFAULT 100,
                gifts INTEGER DEFAULT 0,
                invited INTEGER DEFAULT 0,
                earned INTEGER DEFAULT 0
            )
            """
        )

        await db.commit()


async def get_user(user_id: int, username: str = ""):
    async with connect(DB_NAME) as db:
        async with db.execute(
            """
            SELECT stars, gifts, invited, earned
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:

            row = await cursor.fetchone()

            if not row:
                await db.execute(
                    """
                    INSERT INTO users
                    (user_id, username, stars, gifts, invited, earned)
                    VALUES (?, ?, 100, 0, 0, 0)
                    """,
                    (user_id, username),
                )

                await db.commit()

                return {
                    "stars": 100,
                    "gifts": 0,
                    "invited": 0,
                    "earned": 0,
                }

            return {
                "stars": row[0],
                "gifts": row[1],
                "invited": row[2],
                "earned": row[3],
            }


async def update_stars(user_id: int, amount: int):
    async with connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE users
            SET stars = stars + ?
            WHERE user_id = ?
            """,
            (amount, user_id),
        )

        await db.commit()


# ============================================================
# WEBSOCKET CLIENTS
# ============================================================

connected_clients = set()


async def broadcast(data):
    message = json.dumps(data, ensure_ascii=False)

    dead_clients = []

    for ws in list(connected_clients):
        try:
            await ws.send_str(message)
        except Exception:
            dead_clients.append(ws)

    for ws in dead_clients:
        connected_clients.discard(ws)


# ============================================================
# TELEGRAM /START
# ============================================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):

    await get_user(
        message.from_user.id,
        message.from_user.username or "",
    )

    keyboard_rows = []

    if WEBAPP_URL:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 Запустить GiftsMMS",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="📢 Канал @ECLIPSEDLF",
                url="https://t.me/ECLIPSEDLF",
            )
        ]
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=keyboard_rows
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Добро пожаловать в **GiftsMMS** 🎉\n\n"
        f"На ваш баланс зачислено 100 ⭐.\n\n"
        f"Адрес TON: `{TON_WALLET}`",
        reply_markup=kb,
        parse_mode="Markdown",
    )


# ============================================================
# STARS PAYMENT
# ============================================================

@dp.message(F.text == "/buy_stars")
async def buy_stars(message: types.Message):

    prices = [
        LabeledPrice(
            label="100 Stars",
            amount=100,
        )
    ]

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Пополнение GiftsMMS",
        description="Покупка 100 Stars",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="buy-stars",
        payload="stars_pack_100",
    )


@dp.pre_checkout_query()
async def process_pre_checkout(
    pre_checkout_query: types.PreCheckoutQuery,
):

    await bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
    )


@dp.message(F.successful_payment)
async def process_pay(message: types.Message):

    raw_amount = 100

    await update_stars(
        message.from_user.id,
        raw_amount,
    )

    await message.answer(
        f"🎉 Оплата прошла успешно!\n"
        f"Вам зачислено {raw_amount} ⭐."
    )


# ============================================================
# WEB APP ROUTES
# ============================================================

routes = web.RouteTableDef()


# ============================================================
# MAIN PAGE
# ============================================================

@routes.get("/")
async def index_handler(request):

    if not os.path.isfile(INDEX_FILE):
        return web.Response(
            text=(
                "Web App не найден.\n\n"
                "Создай файл:\n"
                "webapp/index.html"
            ),
            status=500,
            content_type="text/plain",
        )

    return web.FileResponse(INDEX_FILE)


# ============================================================
# HEALTH CHECK
# ============================================================

@routes.get("/health")
async def health_handler(request):

    return web.json_response(
        {
            "status": "ok",
            "service": "GiftsMMS",
        }
    )


# ============================================================
# WEBSOCKET
# ============================================================

@routes.get("/ws")
async def websocket_handler(request):

    ws = web.WebSocketResponse()

    await ws.prepare(request)

    connected_clients.add(ws)

    try:

        await ws.send_str(
            json.dumps(
                {
                    "type": "connected",
                    "status": "ok",
                },
                ensure_ascii=False,
            )
        )

        async for msg in ws:

            if msg.type == WSMsgType.TEXT:

                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:

                    await ws.send_str(
                        json.dumps(
                            {
                                "type": "error",
                                "error": "Invalid JSON",
                            }
                        )
                    )

                    continue

                action = data.get("action")

                if action == "ping":

                    await ws.send_str(
                        json.dumps(
                            {
                                "type": "pong"
                            }
                        )
                    )

                elif action == "get_user":

                    try:
                        user_id = int(
                            data.get("user_id", 0)
                        )

                        if not user_id:
                            raise ValueError

                        user = await get_user(user_id)

                        await ws.send_str(
                            json.dumps(
                                {
                                    "type": "user",
                                    "user": user,
                                },
                                ensure_ascii=False,
                            )
                        )

                    except (ValueError, TypeError):

                        await ws.send_str(
                            json.dumps(
                                {
                                    "type": "error",
                                    "error": "Invalid user_id",
                                }
                            )
                        )

            elif msg.type == WSMsgType.ERROR:

                logging.error(
                    "WebSocket error: %s",
                    ws.exception(),
                )

    finally:

        connected_clients.discard(ws)

    return ws


# ============================================================
# USER API
# ============================================================

@routes.get("/api/user")
async def api_user(request):

    try:
        user_id = int(
            request.query.get("user_id", "0")
        )
    except ValueError:

        return web.json_response(
            {
                "error": "Invalid user_id"
            },
            status=400,
        )

    if not user_id:

        return web.json_response(
            {
                "error": "No user_id"
            },
            status=400,
        )

    user = await get_user(user_id)

    return web.json_response(user)


# ============================================================
# REQUEST GIFT
# ============================================================

@routes.post("/api/request_gift")
async def api_request_gift(request):

    try:
        data = await request.json()
    except Exception:

        return web.json_response(
            {
                "error": "Invalid JSON"
            },
            status=400,
        )

    try:
        user_id = int(data.get("user_id", 0))
    except (ValueError, TypeError):

        return web.json_response(
            {
                "error": "Invalid user_id"
            },
            status=400,
        )

    gift_name = str(
        data.get(
            "gift_name",
            "Telegram Gift",
        )
    )[:100]

    if not user_id:

        return web.json_response(
            {
                "error": "No user_id"
            },
            status=400,
        )

    user = await get_user(user_id)

    if user["stars"] < 500:

        return web.json_response(
            {
                "error": "Недостаточно звезд",
                "required": 500,
                "balance": user["stars"],
            },
            status=400,
        )

    await update_stars(
        user_id,
        -500,
    )

    if ADMIN_ID != 0:

        try:

            await bot.send_message(
                ADMIN_ID,
                "📥 <b>НОВАЯ ЗАЯВКА НА ПОДАРОК</b>\n\n"
                f"👤 Пользователь: <code>{user_id}</code>\n"
                f"🎁 Подарок: <b>{gift_name}</b>",
                parse_mode="HTML",
            )

        except Exception as e:

            logging.error(
                "Не удалось отправить заявку админу: %s",
                e,
            )

    new_user = await get_user(user_id)

    return web.json_response(
        {
            "status": "ok",
            "balance": new_user["stars"],
        }
    )


# ============================================================
# STATIC FILES
# ============================================================

if not os.path.isdir(WEBAPP_DIR):
    os.makedirs(
        WEBAPP_DIR,
        exist_ok=True,
    )


# ============================================================
# APP
# ============================================================

app = web.Application()

app.add_routes(routes)

# CSS / JS / картинки из webapp
app.router.add_static(
    "/webapp/",
    path=WEBAPP_DIR,
    name="webapp",
)


# ============================================================
# START
# ============================================================

async def main():

    await init_db()

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    logging.info(
        "Web server запущен на 0.0.0.0:%s",
        PORT,
    )

    logging.info(
        "Web App: %s",
        WEBAPP_URL or "WEBAPP_URL не задан",
    )

    logging.info(
        "Index: %s",
        INDEX_FILE,
    )

    # Удаляем webhook перед polling.
    # Это нормально, если бот работает именно через polling.
    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

    except Exception as e:

        logging.error(
            "Ошибка удаления webhook: %s",
            e,
        )

    logging.info(
        "Запуск Telegram polling..."
    )

    try:

        await dp.start_polling(bot)

    finally:

        await bot.session.close()

        await runner.cleanup()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logging.info(
            "Бот остановлен."
  )
