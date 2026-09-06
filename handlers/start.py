from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from database.db import create_user, get_user
from keyboards.menus import menu

router = Router()

@router.message(CommandStart())
async def start(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        ref = None
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) != message.from_user.id:
            ref = int(parts[1])
        await create_user(message.from_user.id, message.from_user.username, ref)
        text = "Добро пожаловать! Баланс создан: 0 виртуальных кредитов."
    else:
        text = "С возвращением!"
    await message.answer(text, reply_markup=menu)
