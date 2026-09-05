import os
from sys import exit
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    exit("CRITICAL ERROR: BOT_TOKEN is missing in environment variables.")

if not DATABASE_URL:
    exit("CRITICAL ERROR: DATABASE_URL is missing in environment variables.")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    ADMIN_ID = 0

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com/index.html")
