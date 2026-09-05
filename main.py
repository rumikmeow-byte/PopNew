import asyncio
import json
import random
from html import escape
from typing import Dict, Any
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL
import db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальное состояние игры Jackpot
CURRENT_ROOM_ID = 1
JACKPOT_TIMER_TASK = None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без_юзернейма"

    current_balance = await db.get_balance(user_id)
    if current_balance is None:
        await db.update_balance(user_id, 0)

    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE users SET username=$1 WHERE user_id=$2", username, user_id)

    balance = await db.get_balance(user_id) or 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎡 Войти в Jackpot / Рулетку", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="⭐ +100", callback_data="add_100"),
         InlineKeyboardButton(text="⭐ +500", callback_data="add_500"),
         InlineKeyboardButton(text="⭐ +1000", callback_data="add_1000")]
    ])

    await message.answer(
        f"🎁 <b>Добро пожаловать в GiftsMMS!</b>\n\n"
        f"💰 Твой баланс: <b>{balance} ⭐</b>\n"
        f"🎡 Нажми кнопку ниже, чтобы открыть мультиплеер и сделать ставку!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("add_"))
async def add_balance_instant(callback: types.CallbackQuery):
    try:
        amount = int(callback.data.split("_")[1])
        user_id = callback.from_user.id

        await db.update_balance(user_id, amount, f"Пополнение на {amount}")
        new_balance = await db.get_balance(user_id)

        await callback.answer(f"✅ +{amount} ⭐ зачислено!", show_alert=True)
        await callback.message.answer(f"⭐ Новый баланс: {new_balance} ⭐")
    except Exception:
        await callback.answer("Ошибка пополнения", show_alert=True)

# Функция подведения итогов Jackpot
async def finish_jackpot_round():
    global CURRENT_ROOM_ID, JACKPOT_TIMER_TASK
    
    await asyncio.sleep(30)  # Таймер на 30 секунд после первой ставки

    bets = await db.get_jackpot_room_bets(CURRENT_ROOM_ID)
    if not bets:
        JACKPOT_TIMER_TASK = None
        return

    total_pot = sum(b["total_bet"] for b in bets)
    
    # Если ставка всего одна — возвращаем средства и отменяем раунд
    if len(bets) == 1:
        single_user = bets[0]
        await db.update_balance(single_user["user_id"], single_user["total_bet"], "Возврат одиночной ставки")
        await bot.send_message(
            single_user["user_id"],
            f"⚠️ Раунд отменён: недостаточно участников. Ставка {single_user['total_bet']} ⭐ возвращена."
        )
        await db.clear_jackpot_room(CURRENT_ROOM_ID)
        JACKPOT_TIMER_TASK = None
        return

    # Логика выбора победителя на основе шансов (колеса)
    ticket = random.uniform(0, total_pot)
    current_ticket = 0
    winner = None

    for b in bets:
        current_ticket += b["total_bet"]
        if ticket <= current_ticket:
            winner = b
            break

    if not winner:
        winner = bets[-1]

    win_amount = total_pot
    winner_chance = round((winner["total_bet"] / total_pot) * 100, 2)

    # Начисление выигрыша
    await db.update_balance(winner["user_id"], win_amount, f"Выигрыш Jackpot в комнате #{CURRENT_ROOM_ID}")

    # Оповещение участников
    for b in bets:
        msg = (
            f"🎉 <b>Итоги Jackpot (Комната #{CURRENT_ROOM_ID})!</b>\n\n"
            f"🏆 Победитель: @{escape(winner['username'])}\n"
            f"💰 Общий банк: <b>{win_amount} ⭐</b>\n"
            f"📊 Шанс победителя: <b>{winner_chance}%</b>\n"
        )
        try:
            await bot.send_message(b["user_id"], msg, parse_mode="HTML")
        except Exception:
            pass

    # Очистка комнаты и запуск нового раунда
    await db.clear_jackpot_room(CURRENT_ROOM_ID)
    CURRENT_ROOM_ID += 1
    JACKPOT_TIMER_TASK = None

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    global JACKPOT_TIMER_TASK
    try:
        payload = json.loads(message.web_app_data.data)
        bet = int(payload.get("bet", 0))
        user_id = message.from_user.id
        username = message.from_user.username or "без_юзернейма"

        balance = await db.get_balance(user_id) or 0

        if bet < 15:
            await message.answer("❌ Минимальная ставка — 15 ⭐")
            return
        if balance < bet:
            await message.answer("❌ Недостаточно средств!")
            return

        # Списание баланса и добавление в Jackpot
        await db.update_balance(user_id, -bet, f"Ставка Jackpot {bet}")
        await db.add_jackpot_bet(CURRENT_ROOM_ID, user_id, username, bet)

        bets = await db.get_jackpot_room_bets(CURRENT_ROOM_ID)
        total_pot = sum(b["total_bet"] for b in bets)

        await message.answer(
            f"✅ Ставка <b>{bet} ⭐</b> принята в Jackpot!\n"
            f"💰 Общий банк комнаты: <b>{total_pot} ⭐</b>\n"
            f"👥 Игроков в раунде: {len(bets)}",
            parse_mode="HTML"
        )

        # Старт таймера раунда при первой ставке
        if JACKPOT_TIMER_TASK is None:
            JACKPOT_TIMER_TASK = asyncio.create_task(finish_jackpot_round())

    except Exception:
        await message.answer("❌ Ошибка при приёме ставки.")

async def on_startup():
    await db.init_db()
    print("✅ База данных подключена, таблицы инициализированы.")

async def main():
    dp.startup.register(on_startup)
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
