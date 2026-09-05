import random
import time

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import (
    BOT_NAME,
    MAX_DEPOSIT_STARS,
    TON_TO_STARS_RATE,
    BOT_WALLET_ADDRESS,
)

from db import (
    get_user,
    update_balance,
    set_free_case_time,
    reset_share_count,
    increment_share_count,
    add_referral,
    get_referral_stats,
    create_battle,
    get_battle_info,
    get_battle_players,
    add_player_to_battle,
    get_active_battles,
    set_ton_address,
)

from keyboards import (
    main_menu,
    back_button,
    deposit_menu,
    battle_main_menu,
    battle_currency_choice,
    battle_bet_buttons,
    battle_ton_bet_buttons,
    battle_control_buttons,
)

from utils import (
    check_all_subscriptions,
    get_unsubscribed_channels,
    check_transaction,
)


handlers_router = Router()


class BattleStates(StatesGroup):
    waiting_custom_bet = State()
    waiting_custom_ton_bet = State()


@handlers_router.message(Command("start"))
async def start_cmd(message: types.Message):
    args = message.text.split()

    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(
                args[1].split("_", 1)[1]
            )

            if referrer_id != message.from_user.id:
                user = await get_user(
                    message.from_user.id
                )

                if (
                    user["ref_count"] == 0
                    and user["balance"] == 0
                ):
                    await add_referral(
                        referrer_id,
                        message.from_user.id,
                    )

        except (ValueError, IndexError):
            pass

    await message.answer(
        f"🎁 Добро пожаловать в {BOT_NAME}!\n"
        "Открывай бесплатный кейс, "
        "приглашай друзей и выигрывай звёзды!",
        reply_markup=main_menu(),
    )


@handlers_router.callback_query(F.data == "back_main")
async def back_main(
    callback: types.CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.edit_text(
        f"Главное меню {BOT_NAME}",
        reply_markup=main_menu(),
    )

    await callback.answer()


@handlers_router.callback_query(F.data == "free_case")
async def free_case_handler(
    callback: types.CallbackQuery,
):
    user_id = callback.from_user.id
    user = await get_user(user_id)

    now = int(time.time())

    if now - user["free_case_time"] < 86400:
        await callback.answer(
            "⏳ Бесплатный кейс будет доступен через 24 часа!",
            show_alert=True,
        )
        return

    if not await check_all_subscriptions(
        callback.bot,
        user_id,
    ):
        missing = await get_unsubscribed_channels(
            callback.bot,
            user_id,
        )

        channels_text = "\n".join(
            f"• @{ch}" for ch in missing
        )

        await callback.message.edit_text(
            "❌ Вы не подписаны на следующие каналы:\n"
            f"{channels_text}\n\n"
            "Подпишитесь и нажмите «Проверить».",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Проверить подписку",
                            callback_data="check_sub_free",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="back_main",
                        )
                    ],
                ]
            ),
        )

        await callback.answer()
        return

    if user["shared_count"] < 2:
        bot_info = await callback.bot.get_me()

        link = (
            f"https://t.me/{bot_info.username}"
            f"?start=ref_{user_id}"
        )

        await callback.message.edit_text(
            "👥 Чтобы открыть бесплатный кейс, "
            "нужно поделиться ссылкой с 2 друзьями.\n\n"
            "1. Нажмите «Поделиться».\n"
            "2. Отправьте сообщение друзьям.\n"
            "3. После отправки нажмите "
            "«Я поделился!».\n\n"
            f"Прогресс: {user['shared_count']}/2\n\n"
            f"Ваша ссылка:\n{link}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📤 Поделиться",
                            url=(
                                "https://t.me/share/url"
                                f"?url={link}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✅ Я поделился!",
                            callback_data="share_confirm",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="back_main",
                        )
                    ],
                ]
            ),
        )

        await callback.answer()
        return

    reward = random.choice([1, 5, 10])

    await update_balance(
        user_id,
        reward,
    )

    await set_free_case_time(
        user_id,
        now,
    )

    await reset_share_count(user_id)

    await callback.message.edit_text(
        f"🎉 Вы открыли бесплатный кейс "
        f"и получили {reward} ⭐!\n\n"
        "Следующий кейс будет доступен через 24 часа.",
        reply_markup=main_menu(),
    )

    await callback.answer()


@handlers_router.callback_query(F.data == "share_confirm")
async def share_confirm(
    callback: types.CallbackQuery,
):
    user_id = callback.from_user.id

    user = await get_user(user_id)

    if user["shared_count"] >= 2:
        await callback.answer(
            "✅ Вы уже выполнили условие.",
            show_alert=True,
        )
        return

    await increment_share_count(user_id)

    user = await get_user(user_id)

    if user["shared_count"] >= 2:
        await callback.answer(
            "✅ Отлично! Теперь можно открыть кейс.",
            show_alert=True,
        )

        await free_case_handler(callback)

    else:
        await callback.answer(
            f"✅ Прогресс: "
            f"{user['shared_count']}/2",
            show_alert=True,
        )


@handlers_router.callback_query(
    F.data == "check_sub_free"
)
async def check_sub_free(
    callback: types.CallbackQuery,
):
    if await check_all_subscriptions(
        callback.bot,
        callback.from_user.id,
    ):
        await callback.answer(
            "✅ Подписка подтверждена!",
            show_alert=True,
        )

        await free_case_handler(callback)

    else:
        await callback.answer(
            "❌ Вы всё ещё не подписаны "
            "на все каналы!",
            show_alert=True,
        )


@handlers_router.callback_query(F.data == "profile")
async def profile(
    callback: types.CallbackQuery,
):
    user = await get_user(
        callback.from_user.id
    )

    ref_count, ref_earned = (
        await get_referral_stats(
            callback.from_user.id
        )
    )

    next_free = (
        user["free_case_time"]
        + 86400
        - int(time.time())
    )

    if next_free <= 0:
        free_status = "✅ доступен"
    else:
        free_status = (
            f"⏳ через "
            f"{next_free // 3600}ч "
            f"{(next_free % 3600) // 60}м"
        )

    text = (
        f"👤 Профиль в {BOT_NAME}\n"
        f"Баланс: {user['balance']} ⭐\n"
        f"Приглашено: {ref_count}\n"
        f"Заработано: {ref_earned} ⭐\n"
        f"Бесплатный кейс: {free_status}"
    )

    if user["ton_address"]:
        text += (
            "\nTON-адрес: "
            f"`{user['ton_address']}`"
        )

    await callback.message.edit_text(
        text,
        reply_markup=back_button(),
        parse_mode="Markdown",
    )

    await callback.answer()


@handlers_router.callback_query(F.data == "referrals")
async def referrals(
    callback: types.CallbackQuery,
):
    user_id = callback.from_user.id

    count, earned = (
        await get_referral_stats(user_id)
    )

    bot_info = await callback.bot.get_me()

    link = (
        f"https://t.me/{bot_info.username}"
        f"?start=ref_{user_id}"
    )

    await callback.message.edit_text(
        "👥 Приглашайте друзей "
        "и получайте 1 звезду за каждого!\n\n"
        f"Приглашено: {count}\n"
        f"Заработано: {earned} ⭐\n\n"
        f"Ваша ссылка:\n{link}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📤 Поделиться",
                        url=(
                            "https://t.me/share/url"
                            f"?url={link}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="back_main",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


@handlers_router.callback_query(F.data == "deposit")
async def deposit_menu_handler(
    callback: types.CallbackQuery,
):
    await callback.message.edit_text(
        "💰 Выберите сумму пополнения:",
        reply_markup=deposit_menu(),
    )

    await callback.answer()


@handlers_router.callback_query(
    F.data.startswith("dep_")
)
async def deposit_amount(
    callback: types.CallbackQuery,
):
    try:
        amount = int(
            callback.data.split("_", 1)[1]
        )
    except ValueError:
        await callback.answer(
            "❌ Некорректная сумма.",
            show_alert=True,
        )
        return

    if amount <= 0:
        await callback.answer(
            "❌ Некорректная сумма.",
            show_alert=True,
        )
        return

    if amount > MAX_DEPOSIT_STARS:
        await callback.answer(
            f"❌ Максимум "
            f"{MAX_DEPOSIT_STARS} ⭐ за раз.",
            show_alert=True,
        )
        return

    if not BOT_WALLET_ADDRESS:
        await callback.answer(
            "❌ TON-кошелёк бота не настроен.",
            show_alert=True,
        )
        return

    if TON_TO_STARS_RATE <= 0:
        await callback.answer(
            "❌ Неверный курс TON/Stars.",
            show_alert=True,
        )
        return

    user_id = callback.from_user.id

    ton_amount = (
        amount / TON_TO_STARS_RATE
    )

    comment = (
        f"dep_{user_id}_{amount}_"
        f"{int(time.time())}"
    )

    ton_link = (
        f"ton://transfer/"
        f"{BOT_WALLET_ADDRESS}"
        f"?amount={int(ton_amount * 1e9)}"
        f"&text={comment}"
    )

    await callback.message.edit_text(
        f"💎 Для пополнения на {amount} ⭐ "
        f"переведите {ton_amount:.4f} TON.\n\n"
        f"Адрес:\n"
        f"`{BOT_WALLET_ADDRESS}`\n\n"
        f"Комментарий:\n"
        f"`{comment}`\n\n"
        f"[Открыть Tonkeeper]({ton_link})\n\n"
        "После перевода нажмите "
        "«Проверить оплату».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Проверить оплату",
                        callback_data=(
                            f"check_dep_"
                            f"{comment}_{amount}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="deposit",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )

    await callback.answer()


@handlers_router.callback_query(
    F.data.startswith("check_dep_")
)
async def check_deposit(
    callback: types.CallbackQuery,
):
    parts = callback.data.split("_")

    if len(parts) < 4:
        await callback.answer(
            "❌ Некорректный запрос.",
            show_alert=True,
        )
        return

    try:
        amount = int(parts[-1])
    except ValueError:
        await callback.answer(
            "❌ Некорректная сумма.",
            show_alert=True,
        )
        return

    comment = "_".join(
        parts[2:-1]
    )

    if TON_TO_STARS_RATE <= 0:
        await callback.answer(
            "❌ Неверный курс.",
            show_alert=True,
        )
        return

    ton_amount = (
        amount / TON_TO_STARS_RATE
    )

    if await check_transaction(
        comment,
        ton_amount,
    ):
        await update_balance(
            callback.from_user.id,
            amount,
        )

        await callback.answer(
            f"✅ Пополнение на {amount} ⭐ "
            "подтверждено!",
            show_alert=True,
        )

        await callback.message.edit_text(
            f"✅ Баланс пополнен на "
            f"{amount} ⭐.",
            reply_markup=main_menu(),
        )

    else:
        await callback.answer(
            "❌ Платёж не найден.",
            show_alert=True,
        )


@handlers_router.callback_query(
    F.data == "battle_menu"
)
async def battle_menu(
    callback: types.CallbackQuery,
):
    await callback.message.edit_text(
        "🥊 Батл",
        reply_markup=battle_main_menu(),
    )

    await callback.answer()


@handlers_router.callback_query(
    F.data == "create_battle"
)
async def create_battle_handler(
    callback: types.CallbackQuery,
):
    await callback.message.edit_text(
        "Выберите валюту:",
        reply_markup=battle_currency_choice(),
    )

    await callback.answer()


@handlers_router.callback_query(
    F.data.startswith("battle_currency_")
)
async def choose_currency(
    callback: types.CallbackQuery,
):
    currency = callback.data.split("_")[-1]

    if currency not in ("stars", "ton"):
        await callback.answer(
            "❌ Неверная валюта.",
            show_alert=True,
        )
        return

    user_id = callback.from_user.id

    if not await check_all_subscriptions(
        callback.bot,
        user_id,
    ):
        await callback.answer(
            "❌ Вы не подписаны на каналы!",
            show_alert=True,
        )
        return

    battle_id = await create_battle(
        user_id,
        currency,
    )

    await show_battle(
        callback.message,
        battle_id,
    )

    await callback.answer()


async def show_battle(
    message: types.Message,
    battle_id: int,
    edit: bool = True,
):
    info = await get_battle_info(
        battle_id
    )

    if not info:
        await message.answer(
            "❌ Батл не найден.",
            reply_markup=battle_main_menu(),
        )
        return

    players = await get_battle_players(
        battle_id
    )

    if info["currency"] == "stars":
        total_bank = info["total_bank_stars"]
        currency_symbol = "⭐"
    else:
        total_bank = info["total_bank_ton"]
        currency_symbol = "TON"

    text = (
        f"🎮 Батл #{battle_id}\n"
        f"Валюта: {currency_symbol}\n"
        f"Игроки: {len(players)}/"
        f"{info['max_players']}\n"
        f"Банк: {total_bank} "
        f"{currency_symbol}\n"
        f"Хэш: {info['hash']}\n\n"
    )

    if players:
        text += "👥 Участники:\n"

        for player in players:
            user_id, bet_stars, bet_ton, _ = player

            bet = (
                bet_stars
                if info["currency"] == "stars"
                else bet_ton
            )

            chance = (
                bet / total_bank * 100
                if total_bank > 0
                else 0
            )

            text += (
                f"• {user_id} — "
                f"{chance:.2f}% — "
                f"{bet} {currency_symbol}\n"
            )
    else:
        text += (
            "👥 Пока нет участников.\n"
        )

    if info["status"] == "waiting":
        if info["currency"] == "stars":
            keyboard = battle_bet_buttons(
                battle_id
            )
        else:
            keyboard = battle_ton_bet_buttons(
                battle_id
            )
    else:
        keyboard = battle_control_buttons(
            battle_id
        )

    if edit:
        await message.edit_text(
            text,
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            text,
            reply_markup=keyboard,
        )


@handlers_router.callback_query(
    F.data.startswith("battle_bet_")
)
async def battle_bet_stars(
    callback: types.CallbackQuery,
    state: FSMContext,
):
    parts = callback.data.split("_")

    try:
        battle_id = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer(
            "❌ Некорректный батл.",
            show_alert=True,
        )
        return

    if len(parts) > 3 and parts[3] == "custom":
        await callback.message.edit_text(
            "Введите сумму ставки в звёздах:"
        )

        await state.set_state(
            BattleStates.waiting_custom_bet
        )

        await state.update_data(
            battle_id=battle_id
        )

        await callback.answer()
        return

    try:
        bet = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer(
            "❌ Некорректная ставка.",
            show_alert=True,
        )
        return

    if bet <= 0:
        await callback.answer(
            "❌ Ставка должна быть больше нуля.",
            show_alert=True,
        )
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)

    if user["balance"] < bet:
        await callback.answer(
            f"❌ Недостаточно звёзд.\n"
            f"Баланс: {user['balance']}",
            show_alert=True,
        )
        return

    info = await get_battle_info(
        battle_id
    )

    if not info or info["status"] != "waiting":
        await callback.answer(
            "❌ Батл уже завершён.",
            show_alert=True,
        )
        return

    await update_balance(
        user_id,
        -bet,
    )

    result, msg = await add_player_to_battle(
        battle_id,
        user_id,
        bet_stars=bet,
    )

    if not result:
        await update_balance(
            user_id,
            bet,
        )

        await callback.answer(
            f"❌ {msg}",
            show_alert=True,
        )
        return

    await callback.answer(
        "✅ Вы присоединились!"
    )

    await show_battle(
        callback.message,
        battle_id,
    )


@handlers_router.message(
    BattleStates.waiting_custom_bet
)
async def custom_bet_stars(
    message: types.Message,
    state: FSMContext,
):
    try:
        bet = int(message.text)

        if bet <= 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Введите положительное "
            "целое число."
        )
        return

    data = await state.get_data()

    battle_id = data.get("battle_id")

    if not battle_id:
        await state.clear()
        await message.answer(
            "❌ Батл не найден."
        )
        return

    user_id = message.from_user.id
    user = await get_user(user_id)

    if user["balance"] < bet:
        await message.answer(
            f"❌ Недостаточно звёзд.\n"
            f"Баланс: {user['balance']}"
        )
        return

    info = await get_battle_info(
        battle_id
    )

    if not info or info["status"] != "waiting":
        await message.answer(
            "❌ Батл уже завершён."
        )
        await state.clear()
        return

    await update_balance(
        user_id,
        -bet,
    )

    result, msg = await add_player_to_battle(
        battle_id,
        user_id,
        bet_stars=bet,
    )

    if not result:
        await update_balance(
            user_id,
            bet,
        )

        await message.answer(
            f"❌ {msg}"
        )

        await state.clear()
        return

    await state.clear()

    await message.answer(
        "✅ Вы присоединились!"
    )

    await show_battle(
        message,
        battle_id,
        edit=False,
    )


@handlers_router.callback_query(
    F.data == "list_battles"
)
async def list_battles(
    callback: types.CallbackQuery,
):
    battles = await get_active_battles()

    if not battles:
        text = (
            "📋 Активных батлов нет."
        )
    else:
        text = "📋 Активные батлы:\n"

        for battle in battles:
            (
                battle_id,
                _,
                currency,
                bank_stars,
                bank_ton,
                _,
                max_players,
            ) = battle

            if currency == "stars":
                bank = bank_stars
                symbol = "⭐"
            else:
                bank = bank_ton
                symbol = "TON"

            players = await get_battle_players(
                battle_id
            )

            text += (
                f"• #{battle_id} — "
                f"{bank} {symbol}, "
                f"{len(players)}/{max_players}\n"
            )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 Создать батл",
                    callback_data="create_battle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="battle_menu",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )

    await callback.answer()


@handlers_router.callback_query(
    F.data.startswith("refresh_battle_")
)
async def refresh_battle(
    callback: types.CallbackQuery,
):
    try:
        battle_id = int(
            callback.data.split("_")[-1]
        )
    except ValueError:
        await callback.answer(
            "❌ Некорректный батл.",
            show_alert=True,
        )
        return

    await show_battle(
        callback.message,
        battle_id,
    )

    await callback.answer()


@handlers_router.callback_query(
    F.data == "crash_menu"
)
async def crash_menu_handler(
    callback: types.CallbackQuery,
):
    await callback.message.edit_text(
        "📈 Краш — игра в разработке.",
        reply_markup=back_button(),
    )

    await callback.answer()


@handlers_router.message(Command("setton"))
async def set_ton(
    message: types.Message,
):
    args = message.text.split(
        maxsplit=1
    )

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "/setton EQ... или UQ..."
        )
        return

    address = args[1].strip()

    if not (
        address.startswith("EQ")
        or address.startswith("UQ")
    ):
        await message.answer(
            "❌ Некорректный TON-адрес."
        )
        return

    await set_ton_address(
        message.from_user.id,
        address,
    )

    await message.answer(
        "✅ TON-адрес сохранён."
      )
