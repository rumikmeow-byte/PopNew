from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Бесплатный кейс", callback_data="free_case")],
        [InlineKeyboardButton(text="💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="🥊 Батл", callback_data="battle_menu")],
        [InlineKeyboardButton(text="📈 Краш", callback_data="crash_menu")]
    ])

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def deposit_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 ⭐", callback_data="dep_5")],
        [InlineKeyboardButton(text="10 ⭐", callback_data="dep_10")],
        [InlineKeyboardButton(text="15 ⭐", callback_data="dep_15")],
        [InlineKeyboardButton(text="25 ⭐", callback_data="dep_25")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список каналов", callback_data="admin_list_channels")],
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="➖ Удалить канал", callback_data="admin_remove_channel")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def battle_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Создать батл", callback_data="create_battle")],
        [InlineKeyboardButton(text="📋 Список активных батлов", callback_data="list_battles")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def battle_currency_choice():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Звёзды", callback_data="battle_currency_stars")],
        [InlineKeyboardButton(text="💎 TON", callback_data="battle_currency_ton")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="battle_menu")]
    ])

def battle_bet_buttons(battle_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100 ⭐", callback_data=f"battle_bet_{battle_id}_100")],
        [InlineKeyboardButton(text="500 ⭐", callback_data=f"battle_bet_{battle_id}_500")],
        [InlineKeyboardButton(text="1000 ⭐", callback_data=f"battle_bet_{battle_id}_1000")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data=f"battle_bet_custom_{battle_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_battles")]
    ])

def battle_ton_bet_buttons(battle_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="0.1 TON", callback_data=f"battle_tonbet_{battle_id}_0.1")],
        [InlineKeyboardButton(text="0.5 TON", callback_data=f"battle_tonbet_{battle_id}_0.5")],
        [InlineKeyboardButton(text="1 TON", callback_data=f"battle_tonbet_{battle_id}_1")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data=f"battle_tonbet_custom_{battle_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_battles")]
    ])

def battle_control_buttons(battle_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_battle_{battle_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_battles")]
    ])
