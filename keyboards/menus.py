from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Баланс"), KeyboardButton(text="Пополнить")],
    [KeyboardButton(text="Играть"), KeyboardButton(text="Вывести")],
    [KeyboardButton(text="Поддержка")],
], resize_keyboard=True)
