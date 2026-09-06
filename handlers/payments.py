from aiogram import Router
from aiogram.types import Message, LabeledPrice
from aiogram.filters import Command
from config import settings
from database.db import add_transaction, change_balance, transaction_exists

router = Router()

@router.message(lambda m: m.text == "Пополнить")
async def topup(message: Message):
    stars = 10
    await message.answer_invoice(
        title="Виртуальные кредиты",
        description=f"Покупка {stars * settings.stars_to_credits} виртуальных кредитов",
        payload=f"credits:{message.from_user.id}:{stars}",
        currency="XTR",
        prices=[LabeledPrice(label="Виртуальные кредиты", amount=stars)],
    )

@router.pre_checkout_query()
async def pre_checkout(query):
    await query.answer(ok=True)

@router.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: Message):
    payment = message.successful_payment
    external_id = payment.telegram_payment_charge_id
    if await transaction_exists(external_id):
        return
    stars = payment.total_amount
    credits = stars * settings.stars_to_credits
    await add_transaction(message.from_user.id, "stars", credits, external_id)
    await change_balance(message.from_user.id, credits)
    await message.answer(f"Зачислено {credits} виртуальных кредитов.")

@router.message(lambda m: m.text == "Поддержка")
async def support(message: Message):
    await message.answer(f"Поддержка: @{settings.support_username}")
