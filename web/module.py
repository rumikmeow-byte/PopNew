import logging
import sqlite3
import aiosqlite
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command

# Создаем роутер для модульного подключения хэндлеров
router = Router()

# ==========================================
# 1. БАЗА ДАННЫХ (Инициализация и таблицы)
# ==========================================

async def init_db():
    """Создание необходимых таблиц в базе данных SQLite."""
    async with aiosqlite.connect("database.db") as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance_ton REAL DEFAULT 0.0,
                balance_stars INTEGER DEFAULT 0
            )
        """)
        
        # Таблица покупок/инвентаря
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                price REAL
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int, username: str, first_name: str):
    """Получение или регистрация нового пользователя."""
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT user_id, balance_ton, balance_stars FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute(
                    "INSERT INTO users (user_id, username, first_name, balance_ton, balance_stars) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, first_name, 5.0, 100) # Даем стартовый баланс
                )
                await db.commit()
                return {"user_id": user_id, "balance_ton": 5.0, "balance_stars": 100}
            return {"user_id": user[0], "balance_ton": user[1], "balance_stars": user[2]}

# ==========================================
# 2. ОБРАБОТЧИКИ КОМАНД БОТА (Handlers)
# ==========================================

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Приветственное сообщение с кнопкой запуска Mini App."""
    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text="🚀 Открыть GiftsEzz App",
                web_app=types.WebAppInfo(url="https://your-app.onrender.com") # Замените на ваш URL с Render
            )
        ]]
    )
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Добро пожаловать в **GiftsEzz**!\n"
        f"💰 Ваш баланс: `{user['balance_ton']} TON` | `{user['balance_stars']} ⭐`\n\n"
        f"Нажмите кнопку ниже, чтобы начать играть и покупать NFT:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Просмотр профиля пользователя."""
    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    await message.answer(
        f"👤 **Профиль пользователя**\n"
        f"├ ID: `{user['user_id']}`\n"
        f"├ Баланс TON: `{user['balance_ton']} TON`\n"
        f"└ Баланс Stars: `{user['balance_stars']} ⭐`",
        parse_mode="Markdown"
    )

# Регистрация роутера в главном диспетчере
def register_handlers(dp):
    dp.include_router(router)
