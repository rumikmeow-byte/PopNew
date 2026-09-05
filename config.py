import os
from dotenv import load_dotenv

load_dotenv()

# Обязательные переменные
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))          # Укажи свой Telegram ID
BOT_NAME = os.getenv("BOT_NAME", "PopNew")
DB_NAME = os.getenv("DB_NAME", "bot.db")

# TON настройки
TON_API_KEY = os.getenv("TON_API_KEY")
BOT_WALLET_MNEMONIC = os.getenv("BOT_WALLET_MNEMONIC")
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS")

# Экономические параметры
MAX_DEPOSIT_STARS = int(os.getenv("MAX_DEPOSIT_STARS", 100))
TON_TO_STARS_RATE = float(os.getenv("TON_TO_STARS_RATE", 1.0))

# Проверки
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")
if not ADMIN_ID:
    raise ValueError("Не задан ADMIN_ID в переменных окружения!")
