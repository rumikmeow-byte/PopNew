from aiogram import Router
from aiogram.types import Message
from keyboards.menus import menu
from database.db import get_user

router = Router()

@router.message(lambda m: m.text == "Баланс")
async def balance(message: Message):
    user = await get_user(message.from_user.id)
    await message.answer(f"Ваш баланс: {user['balance'] if user else 0} виртуальных кредитов", reply_markup=menu)

@router.message(lambda m: m.text == "Вывести")
async def withdraw(message: Message):
    await message.answer("Вывод виртуальных кредитов в деньги, Stars или TON недоступен.")
