from aiogram import Router
from aiogram.types import Message
from keyboards.menus import menu

router = Router()

@router.message(lambda m: m.text == "📣 Канал")
async def channel(message: Message):
    await message.answer("📣 Канал проекта: @PopNew", reply_markup=menu)
