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
                ref_count INTEGER DEFAULT 0,
                ref_earned INTEGER DEFAULT 0,
                free_case_time INTEGER DEFAULT 0,
                ton_address TEXT DEFAULT NULL,
                shared_count INTEGER DEFAULT 0,
                last_share_reset INTEGER DEFAULT 0
            )
            """
        )

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
            SELECT balance, ref_count, ref_earned, free_case_time,
                   ton_address, shared_count, last_share_reset
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return {
                "balance": row[0],
                "ref_count": row[1],
                "ref_earned": row[2],
                "free_case_time": row[3],
                "ton_address": row[4],
                "shared_count": row[5],
                "last_share_reset": row[6],
            }
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return {
            "balance": 0,
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


async def add_channel(username: str):
    username = username.replace("@", "").strip()
    if not username:
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (username,))
        await db.commit()


async def remove_channel(username: str):
    username = username.replace("@", "").strip()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM channels WHERE username = ?", (username,))
        await db.commit()


async def get_all_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username FROM channels ORDER BY id") as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def create_battle(creator_id: int, currency: str, max_players: int = 10):
    currency = currency.lower()
    if currency not in ("stars", "ton"):
        raise ValueError("Неверная валюта батла")
    server_seed = secrets.token_hex(32)
    commitment = _seed_commitment(server_seed)
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO battles
            (creator_id, currency, max_players, hash, created_at, server_seed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (creator_id, currency, max_players, commitment, int(time.time()), server_seed),
        )
        battle_id = cursor.lastrowid
        await db.commit()
        return battle_id


async def add_player_to_battle(
    battle_id: int,
    user_id: int,
    bet_stars: int = 0,
    bet_ton: float = 0.0,
    ton_address: str = None,
):
    if bet_stars <= 0 and bet_ton <= 0:
        return False, "Ставка должна быть больше нуля"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT max_players, total_bank_stars, total_bank_ton, status FROM battles WHERE battle_id = ?",
            (battle_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False, "Батл не найден"
        max_players, bank_stars, bank_ton, status = row
        if status != "waiting":
            return False, "Игра уже началась или завершена"
        async with db.execute("SELECT COUNT(*) FROM battle_players WHERE battle_id = ?", (battle_id,)) as cursor:
            count = (await cursor.fetchone())[0]
        if count >= max_players:
            return False, "Достигнуто максимальное количество игроков"
        async with db.execute(
            "SELECT id FROM battle_players WHERE battle_id = ? AND user_id = ?",
            (battle_id, user_id),
        ) as cursor:
            if await cursor.fetchone():
                return False, "Вы уже участвуете"
        await db.execute(
            """
            INSERT INTO battle_players
            (battle_id, user_id, bet_stars, bet_ton, ton_address, joined_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (battle_id, user_id, bet_stars, bet_ton, ton_address, int(time.time())),
        )
        await db.execute(
            """
            UPDATE battles
            SET total_bank_stars = total_bank_stars + ?, total_bank_ton = total_bank_ton + ?
            WHERE battle_id = ?
            """,
            (bet_stars, bet_ton, battle_id),
        )
        await db.commit()
        return True, "Вы присоединились"


async def get_battle_players(battle_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, bet_stars, bet_ton, ton_address FROM battle_players WHERE battle_id = ? ORDER BY id",
            (battle_id,),
        ) as cursor:
            return await cursor.fetchall()


async def get_battle_info(battle_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM battles WHERE battle_id = ?", (battle_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        return {
            "battle_id": row[0],
            "creator_id": row[1],
            "currency": row[2],
            "status": row[3],
            "max_players": row[4],
            "total_bank_stars": row[5],
            "total_bank_ton": row[6],
            "hash": row[7],
            "winner_id": row[8],
            "created_at": row[9],
            "started_at": row[10],
            "ended_at": row[11],
            "server_seed": row[12] if len(row) > 12 else None,
        }


async def get_active_battles():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            """
            SELECT battle_id, creator_id, currency, total_bank_stars,
                   total_bank_ton, hash, max_players, status, winner_id,
                   created_at, started_at, ended_at
            FROM battles
            WHERE status IN ('waiting', 'active')
            ORDER BY battle_id DESC
            """
        ) as cursor:
            return await cursor.fetchall()


async def start_ready_battles(start_delay: int = 3):
    now = int(time.time())
    started = []
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT battle_id, max_players FROM battles WHERE status = 'waiting' ORDER BY battle_id"
        ) as cursor:
            candidates = await cursor.fetchall()
        for battle_id, max_players in candidates:
            async with db.execute(
                "SELECT COUNT(*) FROM battle_players WHERE battle_id = ?",
                (battle_id,),
            ) as cursor:
                count = (await cursor.fetchone())[0]
            if count < 2:
                continue
            async with db.execute(
                "SELECT started_at FROM battles WHERE battle_id = ? AND status = 'waiting'",
                (battle_id,),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                continue
            await db.execute(
                "UPDATE battles SET status = 'active', started_at = ? WHERE battle_id = ? AND status = 'waiting'",
                (now + start_delay, battle_id),
            )
            if max_players <= count:
                await db.execute(
                    "UPDATE battles SET started_at = ? WHERE battle_id = ? AND status = 'active'",
                    (now + 1, battle_id),
                )
            started.append(battle_id)
        await db.commit()
    return started


async def resolve_finished_battles(round_seconds: int = 8):
    now = int(time.time())
    resolved = []
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT battle_id, started_at, server_seed, total_bank_stars FROM battles WHERE status = 'active'"
        ) as cursor:
            battles = await cursor.fetchall()
        for battle_id, started_at, server_seed, total_bank_stars in battles:
            if not started_at or now < started_at + round_seconds:
                continue
            async with db.execute(
                "SELECT user_id, bet_stars FROM battle_players WHERE battle_id = ? ORDER BY id",
                (battle_id,),
            ) as cursor:
                players = await cursor.fetchall()
            winner_id = _weighted_winner(players, f"{server_seed}:{battle_id}") if players else None
            if not winner_id:
                await db.execute(
                    "UPDATE battles SET status = 'finished', ended_at = ? WHERE battle_id = ? AND status = 'active'",
                    (now, battle_id),
                )
                await db.commit()
                resolved.append({"battle_id": battle_id, "winner_id": None, "payout": 0})
                continue
            changed = await db.execute(
                "UPDATE battles SET status = 'finished', winner_id = ?, ended_at = ? WHERE battle_id = ? AND status = 'active'",
                (winner_id, now, battle_id),
            )
            if changed.rowcount != 1:
                await db.rollback()
                continue
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (int(total_bank_stars), winner_id),
            )
            await db.commit()
            resolved.append({"battle_id": battle_id, "winner_id": winner_id, "payout": int(total_bank_stars)})
    return resolved


async def get_battle_snapshot(battle_id: int):
    info = await get_battle_info(battle_id)
    if not info:
        return None
    players = await get_battle_players(battle_id)
    total = sum(max(0, int(p[1])) for p in players)
    payload = {
        "battle_id": battle_id,
        "status": info["status"],
        "currency": info["currency"],
        "max_players": info["max_players"],
        "players_count": len(players),
        "bank_stars": info["total_bank_stars"],
        "bank_ton": info["total_bank_ton"],
        "hash": info["hash"],
        "winner_id": info["winner_id"],
        "created_at": info["created_at"],
        "started_at": info["started_at"],
        "ended_at": info["ended_at"],
        "players": [
            {
                "user_id": p[0],
                "bet_stars": p[1],
                "bet_ton": p[2],
                "chance": round((p[1] / total) * 100, 2) if total else 0,
            }
            for p in players
        ],
    }
    if info["status"] == "finished":
        payload["server_seed"] = info["server_seed"]
        payload["proof"] = _seed_commitment(info["server_seed"] or "")
    return payload
