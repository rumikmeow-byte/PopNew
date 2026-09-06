from aiogram import Router
from aiogram.types import Message
from config import settings

router = Router()

@router.message(lambda m: m.text == "Поддержка")
async def support(message: Message):
    await message.answer(f"Поддержка: @{settings.support_username}")
