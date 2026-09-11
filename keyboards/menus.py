from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📣 Канал")],
    [KeyboardButton(text="👥 Заработать рефералами")],
    [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💸 Вывод")],
], resize_keyboard=True)
