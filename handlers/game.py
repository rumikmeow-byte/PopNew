from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from games.engine import play
from database.db import get_user, make_game

router = Router()

class GameState(StatesGroup):
    stake = State()
    chance = State()

@router.message(F.text == "Играть")
async def game_start(message: Message, state: FSMContext):
    await state.set_state(GameState.stake)
    await message.answer("Введите ставку в виртуальных кредитах:")

@router.message(GameState.stake)
async def game_stake(message: Message, state: FSMContext):
    try: stake = int(message.text)
    except ValueError: return await message.answer("Введите целое число.")
    user = await get_user(message.from_user.id)
    if stake < 1 or not user or user['balance'] < stake:
        return await message.answer("Недостаточно виртуальных кредитов или неверная ставка.")
    await state.update_data(stake=stake)
    await state.set_state(GameState.chance)
    await message.answer("Введите шанс от 1 до 99, например 50:")

@router.message(GameState.chance)
async def game_chance(message: Message, state: FSMContext):
    try: chance = float(message.text.replace(',', '.'))
    except ValueError: return await message.answer("Введите число от 1 до 99.")
    data = await state.get_data(); stake = data['stake']
    try: result = play(stake, chance)
    except ValueError: return await message.answer("Шанс должен быть от 1 до 99.")
    ok = await make_game(message.from_user.id, stake, chance, result['roll'], result['coefficient'], 'win' if result['win'] else 'lose', result['delta'])
    await state.clear()
    if not ok: return await message.answer("Баланс изменился, повторите попытку.")
    user = await get_user(message.from_user.id)
    status = "Успех" if result['win'] else "Неудача"
    await message.answer(f"{status}\nЧисло: {result['roll']}\nИзменение: {result['delta']}\nБаланс: {user['balance']}")
