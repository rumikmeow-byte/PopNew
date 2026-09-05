import os

from dotenv import load_dotenv

load_dotenv()


def get_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} должен быть целым числом"
        ) from exc


def get_float(name: str, default: float = 0.0) -> float:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} должен быть числом"
        ) from exc


BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = get_int("ADMIN_ID", 0)

BOT_NAME = os.getenv(
    "BOT_NAME",
    "PopNew",
)

DB_NAME = os.getenv(
    "DB_NAME",
    "bot.db",
)

TON_API_KEY = os.getenv(
    "TON_API_KEY"
)

BOT_WALLET_MNEMONIC = os.getenv(
    "BOT_WALLET_MNEMONIC"
)

BOT_WALLET_ADDRESS = os.getenv(
    "BOT_WALLET_ADDRESS",
    "",
)

MAX_DEPOSIT_STARS = get_int(
    "MAX_DEPOSIT_STARS",
    100,
)

TON_TO_STARS_RATE = get_float(
    "TON_TO_STARS_RATE",
    1.0,
)


if not BOT_TOKEN:
    raise ValueError(
        "Не задан BOT_TOKEN в переменных окружения Render."
    )

if not ADMIN_ID:
    raise ValueError(
        "Не задан ADMIN_ID в переменных окружения Render."
    )
