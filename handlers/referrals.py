from aiogram import Router
from aiogram.types import Message
from database.db import get_user, get_referral_count
from keyboards.menus import menu

router = Router()


@router.message(lambda m: m.text == "Заработать рефералами")
async def referrals(message: Message):
    bot = await message.bot.get_me()
    link = f"https://t.me/{bot.username}?start={message.from_user.id}"
    count = await get_referral_count(message.from_user.id)
    await message.answer(
        f"👥 Ваша реферальная ссылка:\n{link}\n\n"
        f"Приглашено: {count}\n"
        f"Реферальный процент: 5%",
        reply_markup=menu,
    )
