import hashlib
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
                balance REAL DEFAULT 0,
                ton_balance REAL DEFAULT 0,
                ref_count INTEGER DEFAULT 0,
                ref_earned REAL DEFAULT 0,
                free_case_time INTEGER DEFAULT 0,
                ton_address TEXT DEFAULT NULL,
                shared_count INTEGER DEFAULT 0,
                last_share_reset INTEGER DEFAULT 0
            )
            """
        )
        await _ensure_column(db, "users", "ton_balance", "REAL DEFAULT 0")
        await _ensure_column(db, "users", "balance", "REAL DEFAULT 0")
        await _ensure_column(db, "users", "ref_earned", "REAL DEFAULT 0")

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
        await db.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", ("eclipsedlf",))

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                currency TEXT,
                status TEXT DEFAULT 'waiting',
                max_players INTEGER DEFAULT 10,
                total_bank_stars REAL DEFAULT 0,
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
                bet_stars REAL DEFAULT 0,
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
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()
    return amount


async def update_ton_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ton_balance = ton_balance + ? WHERE user_id = ?", (amount, user_id))
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
        reward = 0.85
        await db.execute(
            "UPDATE users SET balance = balance + ?, ref_count = ref_count + 1, ref_earned = ref_earned + ? WHERE user_id = ?",
            (reward, reward, inviter_id),
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


async def get_all_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username FROM channels ORDER BY id") as cursor:
            rows = await cursor.fetchall()
    return [row[0] for row in rows if row[0]]


async def add_channel(username: str):
    username = username.strip().lstrip("@").strip()
    if not username:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (username,))
        await db.commit()
        return cursor.rowcount > 0


async def create_battle(creator_id: int, currency: str):
    currency = currency.lower().strip()
    if currency not in ("stars", "ton"):
        raise ValueError("Unsupported battle currency")
    seed = f"{creator_id}:{time.time_ns()}"
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO battles(creator_id,currency,status,max_players,hash,created_at,server_seed) VALUES(?,?,?,?,?,?,?)",
            (creator_id, currency, "waiting", 10, _seed_commitment(seed), int(time.time()), seed),
        )
        await db.commit()
        return cur.lastrowid


async def get_battle_info(battle_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT battle_id,creator_id,currency,status,max_players,total_bank_stars,total_bank_ton,hash,winner_id,created_at,started_at,ended_at FROM battles WHERE battle_id=?",
            (battle_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    keys = ("battle_id", "creator_id", "currency", "status", "max_players", "total_bank_stars", "total_bank_ton", "hash", "winner_id", "created_at", "started_at", "ended_at")
    return dict(zip(keys, row))


async def get_battle_players(battle_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id,bet_stars,bet_ton,ton_address FROM battle_players WHERE battle_id=? ORDER BY joined_at",
            (battle_id,),
        ) as cur:
            return await cur.fetchall()


async def add_player_to_battle(battle_id: int, user_id: int, bet_stars: float = 0, bet_ton: float = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT status,max_players,currency FROM battles WHERE battle_id=?", (battle_id,)) as cur:
            battle = await cur.fetchone()
        if not battle:
            return False, "Батл не найден."
        status, max_players, currency = battle
        if status != "waiting":
            return False, "Батл уже запущен."
        async with db.execute("SELECT COUNT(*) FROM battle_players WHERE battle_id=?", (battle_id,)) as cur:
            count = (await cur.fetchone())[0]
        if count >= max_players:
            return False, "В батле уже максимум игроков."
        try:
            await db.execute(
                "INSERT INTO battle_players(battle_id,user_id,bet_stars,bet_ton,joined_at) VALUES(?,?,?,?,?)",
                (battle_id, user_id, float(bet_stars or 0), float(bet_ton or 0), int(time.time())),
            )
        except aiosqlite.IntegrityError:
            return False, "Ты уже в этом батле."
        await db.execute(
            "UPDATE battles SET total_bank_stars=total_bank_stars+?, total_bank_ton=total_bank_ton+? WHERE battle_id=?",
            (float(bet_stars or 0), float(bet_ton or 0), battle_id),
        )
        await db.commit()
    return True, "OK"


async def get_active_battles():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT battle_id,creator_id,currency,total_bank_stars,total_bank_ton,status,max_players FROM battles WHERE status='waiting' ORDER BY battle_id DESC",
        ) as cur:
            return await cur.fetchall()
