import aiohttp

from aiogram import Bot

from config import (
    BOT_WALLET_ADDRESS,
    TON_API_KEY,
)

from db import get_all_channels


async def check_all_subscriptions(
    bot: Bot,
    user_id: int,
) -> bool:
    channels = await get_all_channels()

    if not channels:
        return True

    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=f"@{channel}",
                user_id=user_id,
            )

            if member.status not in (
                "member",
                "administrator",
                "creator",
            ):
                return False

        except Exception:
            return False

    return True


async def get_unsubscribed_channels(
    bot: Bot,
    user_id: int,
) -> list:
    channels = await get_all_channels()

    result = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=f"@{channel}",
                user_id=user_id,
            )

            if member.status not in (
                "member",
                "administrator",
                "creator",
            ):
                result.append(channel)

        except Exception:
            result.append(channel)

    return result


async def check_transaction(
    comment: str,
    expected_amount: float,
) -> bool:
    if not TON_API_KEY:
        return False

    if not BOT_WALLET_ADDRESS:
        return False

    url = (
        "https://toncenter.com/api/v2/"
        "getTransactions"
    )

    params = {
        "address": BOT_WALLET_ADDRESS,
        "limit": 20,
        "api_key": TON_API_KEY,
    }

    timeout = aiohttp.ClientTimeout(
        total=15
    )

    try:
        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                params=params,
            ) as response:

                if response.status != 200:
                    return False

                data = await response.json()

    except (
        aiohttp.ClientError,
        TimeoutError,
        ValueError,
    ):
        return False

    for tx in data.get(
        "result",
        [],
    ):
        in_msg = tx.get(
            "in_msg",
            {},
        )

        source = in_msg.get(
            "source"
        )

        message = in_msg.get(
            "message"
        )

        if (
            source
            and source != BOT_WALLET_ADDRESS
            and message == comment
        ):
            try:
                amount_nano = int(
                    in_msg.get(
                        "value",
                        0,
                    )
                )

                amount_ton = (
                    amount_nano / 1_000_000_000
                )

            except (
                ValueError,
                TypeError,
            ):
                continue

            if (
                abs(
                    amount_ton
                    - expected_amount
                )
                < 0.001
            ):
                return True

    return False
