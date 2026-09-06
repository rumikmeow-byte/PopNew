import os

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import BOT_NAME

router = Router()
SUPPORT_USERNAME = "@Eclipsed_consult"
NEWS_CHANNEL = "@Eclipsedlf"


def app_url(message: types.Message) -> str:
    return os.getenv("WEBAPP_URL", "").strip()


@router.message(Command("open"))
async def open_cmd(message: types.Message):
    url = app_url(message)
    if not url:
        await message.answer(f"{BOT_NAME}: Mini App URL пока не настроен в боте.")
        return
    await message.answer(
        "🎁 Открыть GIFTSMMS",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть Mini App", web_app=WebAppInfo(url=url))]
            ]
        ),
    )


@router.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        f"GIFTSMMS\n\n/open — Mini App\n/profile — профиль\n/tasks — задания\n\n"
        f"📢 Новости: {NEWS_CHANNEL}\n🛟 Поддержка: {SUPPORT_USERNAME}"
    )


@router.message(Command("profile"))
async def profile_cmd(message: types.Message):
    await message.answer("👤 Откройте GIFTSMMS → Профиль, чтобы увидеть Stars, TON, билеты и историю.")


@router.message(Command("tasks"))
async def tasks_cmd(message: types.Message):
    await message.answer("📋 Задания находятся в GIFTSMMS → Задания.")
