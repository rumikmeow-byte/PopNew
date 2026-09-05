import asyncio
import json
import random
from html import escape
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL
import db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без_юзернейма"

    current_balance = await db.get_balance(user_id)
    is_new_user = current_balance is None

    if is_new_user:
        await db.update_balance(user_id, 0)
        
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer_id = int(args[1].split("_")[1])
                if referrer_id != user_id:
                    await db.add_referral(referrer_id, user_id)
                    ref_count = await db.get_referral_count(referrer_id)
                    await bot.send_message(
                        referrer_id, 
                        f"🎉 Новый друг по вашей ссылке! У вас {ref_count} приглашённых."
                    )
            except Exception:
                pass

    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE users SET username=$1 WHERE user_id=$2", username, user_id)

    balance = await db.get_balance(user_id) or 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Открыть GiftsMMS", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="⭐ Пополнить 100", callback_data="add_100"),
         InlineKeyboardButton(text="⭐ Пополнить 500", callback_data="add_500")],
        [InlineKeyboardButton(text="⭐ Пополнить 2500", callback_data="add_2500")],
        [InlineKeyboardButton(text="📊 LIVE", callback_data="live")]
    ])

    await message.answer(
        f"🎁 <b>Добро пожаловать в GiftsMMS!</b>\n\n"
        f"💰 Твой баланс: <b>{balance} ⭐</b>\n"
        f"🔽 Минимальная ставка – 15 ⭐, максимальная – 10 000 ⭐\n\n"
        f"💳 <b>Подключить кошелёк</b> — выбери сумму ниже:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("add_"))
async def add_balance_instant(callback: types.CallbackQuery):
    try:
        amount = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        username = callback.from_user.username or "без_юзернейма"

        await db.update_balance(user_id, amount, f"Пополнение на {amount}")
        new_balance = await db.get_balance(user_id)

        await callback.answer(f"✅ +{amount} ⭐ зачислено!", show_alert=True)
        await callback.message.answer(f"⭐ Новый баланс: {new_balance} ⭐")

        if ADMIN_ID:
            admin_text = (
                f"💰 <b>Пополнение баланса</b>\n"
                f"Пользователь: @{escape(username)} (ID: <code>{user_id}</code>)\n"
                f"Сумма: +{amount} ⭐\n"
                f"Новый баланс: {new_balance} ⭐"
            )
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    except Exception:
        await callback.answer("Ошибка при обработке запроса.", show_alert=True)

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try:
        payload = json.loads(message.web_app_data.data)
        bet = int(payload.get("bet", 0))
        user_id = message.from_user.id
        username = message.from_user.username or "без_юзернейма"
        
        balance = await db.get_balance(user_id) or 0

        if bet < 15:
            await message.answer("❌ Минимальная ставка – 15 ⭐")
            return
        if bet > 10000:
            await message.answer("❌ Максимальная ставка – 10 000 ⭐")
            return
        if balance < bet:
            await message.answer("❌ Недостаточно звёзд!")
            return

        await db.update_balance(user_id, -bet, f"Ставка {bet}")

        is_win = random.choice([True, False])
        if is_win:
            multiplier = round(random.uniform(1.01, 20.0), 2)
            win_amount = int(bet * multiplier)
            await db.update_balance(user_id, win_amount, f"Выигрыш x{multiplier}")
            result_text = f"🎉 <b>ВЫИГРЫШ!</b>\nКоэффициент: x{multiplier}\n+{win_amount} ⭐"
            result = "win"
        else:
            win_amount = 0
            multiplier = 0.0
            result_text = f"😵 <b>ПРОИГРЫШ!</b>\nСтавка {bet} ⭐ сгорела."
            result = "lose"

        await db.save_game(user_id, username, bet, multiplier, win_amount, result)
        
        updated_balance = await db.get_balance(user_id)
        await message.answer(
            f"{result_text}\nТекущий баланс: <b>{updated_balance} ⭐</b>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("❌ Ошибка при обработке ставки.")

@dp.callback_query(F.data == "live")
async def show_live(callback: types.CallbackQuery):
    games = await db.get_last_games(20)
    if not games:
        await callback.message.answer("📊 Пока нет сыгранных игр.")
        await callback.answer()
        return

    text = "📊 <b>Последние игры (LIVE)</b>\n\n"
    for i, row in enumerate(games, 1):
        username = escape(str(row["username"]))
        bet = row["bet"]
        multiplier = row["multiplier"]
        win_amount = row["win_amount"]
        result = row["result"]
        created_at = row["created_at"]
        
        time_str = created_at.strftime("%H:%M") if hasattr(created_at, "strftime") else str(created_at)
        status = "✅" if result == "win" else "❌"
        amount = f"+{win_amount}⭐" if result == "win" else f"-{bet}⭐"
            
        text += f"{i}. @{username} | {status} | {bet}⭐ | x{multiplier:.2f} | {amount} | {time_str}\n"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

async def on_startup():
    await db.init_db()
    print("✅ База данных подключена, таблицы инициализированы.")

async def on_shutdown():
    if db.pool:
        await db.pool.close()
        print("🛑 Пул соединений БД закрыт.")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
