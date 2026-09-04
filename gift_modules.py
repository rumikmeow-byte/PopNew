import json
import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.filters import Command

router = Router()

# ==================== ИНВЕНТАРЬ И РЫНОК ====================

@router.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery, db_pool):
    async with db_pool.acquire() as conn:
        nfts = await conn.fetch(
            "SELECT id, title, status FROM user_nfts WHERE user_id = $1 AND status = 'available'",
            callback.from_user.id
        )
    
    if not nfts:
        await callback.message.edit_text("Ваш инвентарь пуст.", reply_markup=None)
        return

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"Sell: {nft['title']}", callback_query_data=f"sell_nft_{nft['id']}")]
        for nft in nfts
    ])
    await callback.message.edit_text("Ваш инвентарь NFT:", reply_markup=kb)

@router.callback_query(F.data.startswith("sell_nft_"))
async def list_on_market(callback: types.CallbackQuery, db_pool):
    nft_id = int(callback.data.split("_")[2])
    price = 5.0  # Фиксированная цена продажи для примера (в TON)

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Защита от повторного выставления на рынок
            updated = await conn.execute(
                "UPDATE user_nfts SET status = 'on_market', price_ton = $1 WHERE id = $2 AND user_id = $3 AND status = 'available'",
                price, nft_id, callback.from_user.id
            )
            if updated == "UPDATE 0":
                await callback.answer("Ошибка: предмет недоступен для продажи.", show_alert=True)
                return

    await callback.answer(f"NFT выставлен на рынок за {price} TON!", show_alert=True)

# ==================== ЕЖЕДНЕВНАЯ СТАВКА ====================

@router.callback_query(F.data == "daily_free_spin")
async def process_daily_spin(callback: types.CallbackQuery, db_pool):
    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        last_spin = await conn.fetchval("SELECT last_free_spin FROM users WHERE user_id = $1", user_id)
        
        now = datetime.utcnow()
        if last_spin and now < last_spin + timedelta(hours=24):
            time_left = (last_spin + timedelta(hours=24)) - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes = remainder // 60
            await callback.answer(f"Следующая бесплатная ставка через {hours}ч {minutes}мин.", show_alert=True)
            return

        async with conn.transaction():
            await conn.execute(
                "INSERT INTO users (user_id, ton_balance, last_free_spin) VALUES ($1, 0.1, $2) "
                "ON CONFLICT (user_id) DO UPDATE SET ton_balance = users.ton_balance + 0.1, last_free_spin = $2",
                user_id, now
            )
            
    await callback.answer("Вы получили 0.1 TON за ежедневный вход!", show_alert=True)

# ==================== ИГРА МИНЫ ====================

@router.callback_query(F.data == "start_mines")
async def start_mines_game(callback: types.CallbackQuery, db_pool):
    user_id = callback.from_user.id
    mines_count = 3
    field_size = 25
    
    # Генерация безопасного поля на сервере
    field = [False] * field_size
    for pos in random.sample(range(field_size), mines_count):
        field[pos] = True  # True = Мина

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO mine_games (user_id, field, bet_amount, step, is_active)
            VALUES ($1, $2, 0.1, 0, TRUE)
            ON CONFLICT (user_id) DO UPDATE 
            SET field = $2, bet_amount = 0.1, step = 0, is_active = TRUE
        """, user_id, json.dumps(field))

    await callback.message.edit_text("Игра «Мины» началась! Выберите ячейку на поле.")

# ==================== РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ====================

def register_handlers(dp):
    dp.include_router(router)
