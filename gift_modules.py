"""
Модуль расширения для Telegram-бота GiftsMMS
Включает: Инвентарь, Стейкинг, Рынок (Marketplace), Игры (Мины, Апгрейд) и Бесплатные ставки.
"""

import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Состояния FSM ---
class MarketStates(StatesGroup):
    waiting_for_price = State()

class MinesStates(StatesGroup):
    waiting_for_bet = State()
    playing = State()

# --- Вспомогательные функции (Заглушки - адаптируйте под свой main.py/db.py) ---
async def get_db_pool():
    pass

async def get_user_data(user_id: int):
    pass

async def require_subscription(user_id: int, bot) -> bool:
    return True

# --- Инициализация таблиц БД ---
async def init_db_tables(pool):
    async with pool.acquire() as conn:
        # Таблица стейкинга
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS gift_staking (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                nft_id INT NOT NULL,
                staked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ends_at TIMESTAMP NOT NULL,
                apr NUMERIC(5, 2) DEFAULT 53.00,
                status VARCHAR(20) DEFAULT 'active'
            );
        """)
        
        # Таблица маркетплейса
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS marketplace (
                id SERIAL PRIMARY KEY,
                seller_id BIGINT NOT NULL,
                nft_id INT NOT NULL,
                price_ton NUMERIC(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active'
            );
        """)
        
        # Таблица истории игр
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                game_name VARCHAR(50) NOT NULL,
                bet_amount NUMERIC(10, 2) NOT NULL,
                win_amount NUMERIC(10, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Таблица бесплатных ставок (24h cooldown)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS free_bets (
                user_id BIGINT PRIMARY KEY,
                last_claim TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

# --- Хэндлеры и Логика ---

# 1. Инвентарь
async def inventory_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    text = "🎒 **Ваш Инвентарь**\n\nЗдесь отображаются все ваши NFT-подарки."
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📈 Поставить в стейкинг", callback_data="staking_menu"),
        types.InlineKeyboardButton("🏪 Выставить на рынок", callback_data="market_sell")
    )
    kb.add(types.InlineKeyboardButton("« Назад", callback_data="main_menu"))
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

# 2. Стейкинг (53% APR в GRAM)
async def staking_menu_handler(call: types.CallbackQuery):
    text = (
        "📈 **Стейкинг Подарков (NFT)**\n\n"
        "Заморозьте свой NFT подарок на **7 дней** и получайте **53% APR** в токене GRAM!\n\n"
        "Выберите действие:"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("📥 Застейкать NFT", callback_data="stake_nft_select"),
        types.InlineKeyboardButton("📊 Мои активные стейки", callback_data="my_stakes"),
        types.InlineKeyboardButton("« Назад", callback_data="inventory")
    )
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

# 3. Маркетплейс (Продажа / Покупка NFT за TON)
async def market_menu_handler(call: types.CallbackQuery):
    text = (
        "🏪 **Рынок NFT Подарков**\n\n"
        "Здесь вы можете покупать и продавать подарки за TON."
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🛒 Купить NFT", callback_data="market_buy_list"),
        types.InlineKeyboardButton("🏷️ Продать NFT", callback_data="market_sell")
    )
    kb.add(types.InlineKeyboardButton("« Назад", callback_data="main_menu"))
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

# 4. Игры («Мины» и «Апгрейд»)
async def games_menu_handler(call: types.CallbackQuery):
    text = (
        "🎮 **Игровой Раздел**\n\n"
        "Испытайте удачу и приумножьте свои балансы TON или NFT!"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💣 Мины", callback_data="game_mines"),
        types.InlineKeyboardButton("⚡ Апгрейд (Скоро)", callback_data="game_upgrade")
    )
    kb.add(types.InlineKeyboardButton("🎁 Бесплатная ставка (0.1 TON)", callback_data="free_bet_claim"))
    kb.add(types.InlineKeyboardButton("« Назад", callback_data="main_menu"))
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

# 5. Бесплатная ставка (раз в 24 часа)
async def free_bet_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    await call.answer("🎉 Вы получили 0.1 TON для игры! Возвращайтесь через 24 часа.", show_alert=True)

# --- Регистрация хэндлеров ---
def register_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(inventory_handler, lambda c: c.data == "inventory")
    dp.register_callback_query_handler(staking_menu_handler, lambda c: c.data == "staking_menu")
    dp.register_callback_query_handler(market_menu_handler, lambda c: c.data == "market_menu")
    dp.register_callback_query_handler(games_menu_handler, lambda c: c.data == "games_menu")
    dp.register_callback_query_handler(free_bet_handler, lambda c: c.data == "free_bet_claim")
