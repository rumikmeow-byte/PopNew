import aiohttp
from aiogram import Bot
from config import BOT_WALLET_ADDRESS, TON_API_KEY
from db import get_all_channels

async def check_all_subscriptions(bot: Bot, user_id: int) -> bool:
    channels = await get_all_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=f"@{ch}", user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True

async def get_unsubscribed_channels(bot: Bot, user_id: int) -> list:
    channels = await get_all_channels()
    unsub = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=f"@{ch}", user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                unsub.append(ch)
        except Exception:
            unsub.append(ch)
    return unsub

async def check_transaction(comment: str, expected_amount: float) -> bool:
    if not TON_API_KEY:
        return False
    url = f"https://toncenter.com/api/v2/getTransactions?address={BOT_WALLET_ADDRESS}&limit=20&api_key={TON_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "result" in data:
                for tx in data["result"]:
                    in_msg = tx.get("in_msg", {})
                    if in_msg.get("source") != BOT_WALLET_ADDRESS and in_msg.get("message") == comment:
                        amount_nano = int(in_msg.get("value", 0))
                        amount_ton = amount_nano / 1e9
                        if abs(amount_ton - expected_amount) < 0.001:
                            return True
    return False
