import hashlib
import random
import secrets
import string
import time
from pathlib import Path

import aiosqlite

from config import DB_NAME


DB_PATH = Path(DB_NAME)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


async def _ensure_column(db, table: str, column: str, definition: str):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        columns = {row[1] for row in await cursor.fetchall()}
    if column not in columns:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                ton_balance REAL DEFAULT 0,
                ref_count INTEGER DEFAULT 0,
                ref_earned INTEGER DEFAULT 0,
                free_case_time INTEGER DEFAULT 0,
                ton_address TEXT DEFAULT NULL,
                shared_count INTEGER DEFAULT 0,
                last_share_reset INTEGER DEFAULT 0
            )
            """
        )
        await _ensure_column(db, "users", "ton_balance", "REAL DEFAULT 0")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
                inviter_id INTEGER,
                invited_id INTEGER,
                PRIMARY KEY (inviter_id, invited_id)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE
            )
            """
        )
        await db.execute(
            "INSERT OR IGNORE INTO channels (username) VALUES (?)",
            ("eclipsedlf",),
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                currency TEXT,
                status TEXT DEFAULT 'waiting',
                max_players INTEGER DEFAULT 10,
                total_bank_stars INTEGER DEFAULT 0,
                total_bank_ton REAL DEFAULT 0,
                hash TEXT,
                winner_id INTEGER DEFAULT NULL,
                created_at INTEGER,
                started_at INTEGER DEFAULT NULL,
                ended_at INTEGER DEFAULT NULL,
                server_seed TEXT DEFAULT NULL
            )
            """
        )
        await _ensure_column(db, "battles", "server_seed", "TEXT DEFAULT NULL")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS battle_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_id INTEGER,
                user_id INTEGER,
                bet_stars INTEGER DEFAULT 0,
                bet_ton REAL DEFAULT 0,
                ton_address TEXT DEFAULT NULL,
                joined_at INTEGER,
                UNIQUE(battle_id, user_id)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ton_deposits (
                deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tx_hash TEXT UNIQUE NOT NULL,
                amount_ton REAL NOT NULL,
                destination TEXT NOT NULL,
                source_address TEXT DEFAULT NULL,
                status TEXT DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                confirmed_at INTEGER DEFAULT NULL
            )
            """
        )

        await db.commit()


def _seed_commitment(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _weighted_winner(players, seed_material: str):
    weighted = [(row[0], max(0, int(row[1]))) for row in players if int(row[1]) > 0]
    if not weighted:
        return None
    total = sum(weight for _, weight in weighted)
    digest = hashlib.sha256(seed_material.encode("utf-8")).digest()
    ticket = int.from_bytes(digest[:8], "big") % total
    cursor = 0
    for user_id, weight in weighted:
        cursor += weight
        if ticket < cursor:
            return user_id
    return weighted[-1][0]


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            """
            SELECT balance, ton_balance, ref_count, ref_earned, free_case_time,
                   ton_address, shared_count, last_share_reset
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return {
                "balance": row[0],
                "ton_balance": row[1],
                "ref_count": row[2],
                "ref_earned": row[3],
                "free_case_time": row[4],
                "ton_address": row[5],
                "shared_count": row[6],
                "last_share_reset": row[7],
            }
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return {
            "balance": 0,
            "ton_balance": 0,
            "ref_count": 0,
            "ref_earned": 0,
            "free_case_time": 0,
            "ton_address": None,
            "shared_count": 0,
            "last_share_reset": 0,
        }


async def update_balance(user_id: int, amount: float, commission: float = 0.0):
    if amount > 0 and commission > 0:
        amount = amount * (1 - commission)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()
    return amount


async def update_ton_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET ton_balance = ton_balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()
    return amount


async def set_free_case_time(user_id: int, timestamp: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET free_case_time = ? WHERE user_id = ?", (timestamp, user_id))
        await db.commit()


async def set_ton_address(user_id: int, address: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ton_address = ? WHERE user_id = ?", (address, user_id))
        await db.commit()


async def reset_share_count(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET shared_count = 0, last_share_reset = ? WHERE user_id = ?",
            (int(time.time()), user_id),
        )
        await db.commit()


async def increment_share_count(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET shared_count = shared_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def add_referral(inviter_id: int, invited_id: int):
    if inviter_id == invited_id:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO referrals (inviter_id, invited_id) VALUES (?, ?)",
            (inviter_id, invited_id),
        )
        if cursor.rowcount <= 0:
            return False
        await db.execute(
            "UPDATE users SET balance = balance + 1, ref_count = ref_count + 1, ref_earned = ref_earned + 1 WHERE user_id = ?",
            (inviter_id,),
        )
        await db.commit()
        return True


async def get_referral_stats(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (user_id,)) as cursor:
            count = (await cursor.fetchone())[0]
        async with db.execute("SELECT ref_earned FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        return count, (row[0] if row else 0)


# Compatibility for legacy handlers. Real Stars/TON battle wagering is disabled.
async def create_battle(*args, **kwargs):
    return None


async def get_battle_info(*args, **kwargs):
    return None


async def get_battle_players(*args, **kwargs):
    return []


async def add_player_to_battle(*args, **kwargs):
    return False


async def get_active_battles(*args, **kwargs):
    return []
