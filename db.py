import asyncpg
from typing import Optional, List
from config import DATABASE_URL

pool: Optional[asyncpg.Pool] = None

async def init_db() -> None:
    global pool
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=5, max_size=20)

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(64) DEFAULT 'без_юзернейма',
                balance INT DEFAULT 0,
                referrer_id BIGINT DEFAULT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                username VARCHAR(64),
                bet INT NOT NULL,
                multiplier NUMERIC(5, 2) NOT NULL,
                win_amount INT NOT NULL,
                result VARCHAR(10) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

async def get_balance(user_id: int) -> Optional[int]:
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)

async def update_balance(user_id: int, amount: int, reason: str = "") -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, balance)
            VALUES ($1, GREATEST(0, $2))
            ON CONFLICT (user_id) DO UPDATE 
            SET balance = GREATEST(0, users.balance + $2);
        """, user_id, amount)

async def add_referral(referrer_id: int, new_user_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET referrer_id = $1 WHERE user_id = $2 AND referrer_id IS NULL",
            referrer_id, new_user_id
        )

async def get_referral_count(referrer_id: int) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE referrer_id = $1", referrer_id)

async def save_game(user_id: int, username: str, bet: int, multiplier: float, win_amount: int, result: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO games (user_id, username, bet, multiplier, win_amount, result)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, user_id, username, bet, multiplier, win_amount, result)

async def get_last_games(limit: int = 20) -> List[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT username, bet, multiplier, win_amount, result, created_at 
            FROM games 
            ORDER BY id DESC 
            LIMIT $1
        """, limit)
