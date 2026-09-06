import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_id: int = int(os.getenv("ADMIN_ID", "0"))
    db_path: str = os.getenv("DB_PATH", "data.sqlite3")
    referral_percent: float = float(os.getenv("REFERRAL_PERCENT", "5"))
    support_username: str = os.getenv("SUPPORT_USERNAME", "support")
    port: int = int(os.getenv("PORT", "10000"))
    stars_to_credits: int = int(os.getenv("STARS_TO_CREDITS", "100"))
    min_stake: int = int(os.getenv("MIN_STAKE", "1"))
    max_stake: int = int(os.getenv("MAX_STAKE", "100000"))

settings = Settings()
