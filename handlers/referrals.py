from aiogram import Router
from aiogram.types import Message
from keyboards.menus import menu

router = Router()

@router.message(lambda m: m.text == "Заработать рефералами")
async def referrals(message: Message):
    bot = await message.bot.get_me()
    link = f"https://t.me/{bot.username}?start={message.from_user.id}"
    await message.answer(
        f"👥 Ваша реферальная ссылка:\n{link}\n\nРеферальный процент: 5%",
        reply_markup=menu,
    )
