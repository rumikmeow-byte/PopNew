from aiogram import Router, F, types
from aiogram.filters import Command

from config import ADMIN_ID, BOT_NAME

from db import (
    get_all_channels,
    add_channel,
    remove_channel,
)

from keyboards import (
    admin_panel,
    back_button,
)


admin_router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@admin_router.message(
    Command("admin_panel")
)
async def admin_panel_cmd(
    message: types.Message,
):
    if not is_admin(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Недостаточно прав."
        )
        return

    await message.answer(
        f"🔧 Админ панель {BOT_NAME}:",
        reply_markup=admin_panel(),
    )


@admin_router.callback_query(
    F.data == "admin_list_channels"
)
async def list_channels(
    callback: types.CallbackQuery,
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Недостаточно прав."
        )
        return

    channels = await get_all_channels()

    if channels:
        text = (
            "📋 Каналы для проверки:\n"
            + "\n".join(
                f"• @{ch}"
                for ch in channels
            )
        )
    else:
        text = "📋 Список каналов пуст."

    await callback.message.edit_text(
        text,
        reply_markup=admin_panel(),
    )

    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_add_channel"
)
async def add_channel_prompt(
    callback: types.CallbackQuery,
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Недостаточно прав."
        )
        return

    await callback.message.edit_text(
        "Введите юзернейм канала:\n\n"
        "/add_channel username",
        reply_markup=back_button(),
    )

    await callback.answer()


@admin_router.message(
    Command("add_channel")
)
async def add_channel_cmd(
    message: types.Message,
):
    if not is_admin(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Недостаточно прав."
        )
        return

    args = message.text.split(
        maxsplit=1
    )

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "/add_channel username"
        )
        return

    username = (
        args[1]
        .replace("@", "")
        .strip()
    )

    if not username:
        await message.answer(
            "❌ Укажите username канала."
        )
        return

    await add_channel(username)

    await message.answer(
        f"✅ Канал @{username} добавлен."
    )


@admin_router.message(
    Command("remove_channel")
)
async def remove_channel_cmd(
    message: types.Message,
):
    if not is_admin(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Недостаточно прав."
        )
        return

    args = message.text.split(
        maxsplit=1
    )

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "/remove_channel username"
        )
        return

    username = (
        args[1]
        .replace("@", "")
        .strip()
    )

    await remove_channel(username)

    await message.answer(
        f"✅ Канал @{username} удалён."
        )
