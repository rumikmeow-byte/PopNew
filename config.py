import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла (если он есть локально)
load_dotenv()

# Основные токены и ключи
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
TON_API_KEY = os.getenv("TON_API_KEY")
BOT_WALLET_MNEMONIC = os.getenv("BOT_WALLET_MNEMONIC")
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")
