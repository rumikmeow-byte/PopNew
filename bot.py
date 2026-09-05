import os
import json
import random
import asyncio
import logging
from aiosqlite import connect
from aiohttp import web, WSMsgType
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
TON_WALLET = os.getenv("TON_WALLET", "UQA6OOWd_V_-asdDgsjiHK3OYTp-FjGihgFNxpSg__dHM1h8")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
PORT = int(os.getenv("PORT", 8080))

GAME_FEE = 0.10     # 10% комиссия на игры
DEPOSIT_FEE = 0.05  # 5% комиссия на пополнение

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_NAME = "database.db"

async def init_db():
    async with connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                stars INTEGER DEFAULT 100,
                gifts INTEGER DEFAULT 0,
                invited INTEGER DEFAULT 0,
                earned INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(user_id: int, username: str = ""):
    async with connect(DB_NAME) as db:
        async with db.execute("SELECT stars, gifts, invited, earned FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
                await db.commit()
                return {"stars": 100, "gifts": 0, "invited": 0, "earned": 0}
            return {"stars": row[0], "gifts": row[1], "invited": row[2], "earned": row[3]}

async def update_stars(user_id: int, amount: int):
    async with connect(DB_NAME) as db:
        await db.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

connected_clients = set()
game_state = {"status": "waiting", "multiplier": 1.00, "crash_point": 1.00, "time_left": 10}

battle_game = {
    "game_id": 291590,
    "players": [],
    "total_bank": 0,
    "status": "waiting"
}

async def broadcast(data):
    msg = json.dumps(data)
    for ws in list(connected_clients):
        try:
            await ws.send_str(msg)
        except Exception:
            connected_clients.remove(ws)

async def crash_game_loop():
    global game_state
    while True:
        game_state["status"] = "waiting"
        game_state["crash_point"] = round(random.uniform(1.00, 23.00), 2)
        
        for t in range(10, 0, -1):
            game_state["time_left"] = t
            await broadcast({"type": "tick", "time": t, "status": "waiting"})
            await asyncio.sleep(1)

        game_state["status"] = "flying"
        current_mult = 1.00
        step = 0.05
        
        while current_mult < game_state["crash_point"]:
            game_state["multiplier"] = round(current_mult, 2)
            await broadcast({"type": "fly", "multiplier": game_state["multiplier"], "status": "flying"})
            await asyncio.sleep(0.1)
            current_mult += step
            if current_mult > 10: step = 0.2
            if current_mult > 15: step = 0.5

        game_state["status"] = "crashed"
        await broadcast({"type": "crash", "multiplier": game_state["crash_point"], "status": "crashed"})
        await asyncio.sleep(3)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await get_user(message.from_user.id, message.from_user.username or "")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить GiftsMMS", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="📢 Канал @ECLIPSEDLF", url="https://t.me/ECLIPSEDLF")]
    ])
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        f"Добро пожаловать в **GiftsMMS** 🎉\n"
        f"На ваш баланс зачислено 100 ⭐!\n"
        f"Адрес для TON депозитов: `{TON_WALLET}`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "/buy_stars")
async def buy_stars(message: types.Message):
    prices = [LabeledPrice(label="100 Stars (комиссия 5%)", amount=100)]
    await bot.send_invoice(
        message.chat.id,
        title="Пополнение баланса GiftsMMS",
        description="Покупка 100 Stars. На баланс поступит 95 ⭐ (комиссия 5%)",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="buy-stars",
        payload="stars_pack_100"
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_pay(message: types.Message):
    raw_amount = 100
    credit_amount = int(raw_amount * (1 - DEPOSIT_FEE))
    await update_stars(message.from_user.id, credit_amount)
    await message.answer(f"🎉 Оплата прошла успешно! Вам зачислено {credit_amount} ⭐ (удержано 5% комиссии).")

routes = web.RouteTableDef()

@routes.get('/ws')
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("action") == "cashout":
                    u_id = data.get("user_id")
                    bet = int(data.get("bet", 0))
                    mult = game_state["multiplier"]
                    
                    if game_state["status"] == "flying":
                        raw_win = bet * mult
                        final_win = int(raw_win * (1 - GAME_FEE))
                        
                        await update_stars(u_id, final_win)
                        new_u = await get_user(u_id)
                        await ws.send_str(json.dumps({
                            "type": "cashout_success", 
                            "win": final_win, 
                            "stars": new_u["stars"]
                        }))
    finally:
        connected_clients.remove(ws)
    return ws

@routes.get('/api/user')
async def api_user(request):
    u_id = int(request.query.get('user_id', 0))
    if not u_id: return web.json_response({'error': 'No user_id'}, status=400)
    return web.json_response(await get_user(u_id))

@routes.post('/api/battle/join')
async def join_battle(request):
    data = await request.json()
    u_id = data.get('user_id')
    name = data.get('name', 'Player')
    bet = int(data.get('bet', 100))

    u_data = await get_user(u_id)
    if u_data['stars'] < bet:
        return web.json_response({'error': 'Недостаточно звезд'}, status=400)

    await update_stars(u_id, -bet)

    colors = ['#9d4edd', '#2196f3', '#f44336', '#ff9800', '#4caf50']
    player_color = colors[len(battle_game["players"]) % len(colors)]

    battle_game["players"].append({
        "user_id": u_id,
        "name": name,
        "bet": bet,
        "color": player_color
    })
    battle_game["total_bank"] += bet

    for p in battle_game["players"]:
        p["chance"] = round((p["bet"] / battle_game["total_bank"]) * 100, 2)

    await broadcast({"type": "battle_update", "game": battle_game})
    return web.json_response({"status": "ok", "game": battle_game})

@routes.post('/api/deposit/ton')
async def deposit_ton(request):
    data = await request.json()
    u_id = data.get('user_id')
    amount_ton = float(data.get('amount', 1.0))

    credit_ton = amount_ton * (1 - DEPOSIT_FEE)
    stars_to_add = int(credit_ton * 100)

    await update_stars(u_id, stars_to_add)
    new_user = await get_user(u_id)

    if ADMIN_ID != 0:
        await bot.send_message(
            ADMIN_ID,
            f"💎 **НОВЫЙ ДЕПОЗИТ TON!**\n\n"
            f"👤 Пользователь: `{u_id}`\n"
            f"Сумма: {amount_ton} TON\n"
            f"Зачислено (-5% комиссия): {stars_to_add} ⭐",
            parse_mode="Markdown"
        )

    return web.json_response({
        "status": "ok", 
        "added_stars": stars_to_add, 
        "balance": new_user["stars"]
    })

@routes.post('/api/request_gift')
async def api_request_gift(request):
    data = await request.json()
    u_id = data.get("user_id")
    gift_name = data.get("gift_name", "Telegram NFT Gift")
    
    u_data = await get_user(u_id)
    if u_data["stars"] < 500:
        return web.json_response({"error": "Недостаточно звезд (нужно 500 ⭐)"}, status=400)

    await update_stars(u_id, -500)

    if ADMIN_ID != 0:
        await bot.send_message(
            ADMIN_ID,
            f"📥 **НОВАЯ ЗАЯВКА НА ВЫДАЧУ NFT!**\n\n"
            f"👤 Пользователь: ID `{u_id}`\n"
            f"🎁 Подарок: **{gift_name}**",
            parse_mode="Markdown"
        )

    return web.json_response({"status": "ok"})

app = web.Application()
app.add_routes(routes)
app.router.add_static('/', path='./webapp', name='webapp')

async def main():
    await init_db()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    asyncio.create_task(crash_game_loop())
    logging.info(f"Сервер запущен на порту {PORT}")
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
