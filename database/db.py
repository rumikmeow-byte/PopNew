import aiosqlite
from config import settings

async def init_db():
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER NOT NULL DEFAULT 0,
            referrer_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stake INTEGER NOT NULL,
            chance REAL NOT NULL,
            roll INTEGER NOT NULL,
            coefficient REAL NOT NULL,
            result TEXT NOT NULL,
            delta INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            amount INTEGER NOT NULL,
            external_id TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return await cur.fetchone()

async def create_user(user_id, username, referrer_id=None):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("INSERT OR IGNORE INTO users(id,username,referrer_id) VALUES(?,?,?)", (user_id, username, referrer_id))
        await db.commit()

async def change_balance(user_id, delta):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE id=?", (delta, user_id))
        await db.commit()

async def make_game(user_id, stake, chance, roll, coefficient, result, delta):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT balance FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        if not row or row[0] < stake:
            await db.rollback(); return False
        await db.execute("UPDATE users SET balance=balance+? WHERE id=?", (delta, user_id))
        await db.execute("INSERT INTO games(user_id,stake,chance,roll,coefficient,result,delta) VALUES(?,?,?,?,?,?,?)", (user_id,stake,chance,roll,coefficient,result,delta))
        await db.commit()
        return True

async def add_transaction(user_id, kind, amount, external_id):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("INSERT INTO transactions(user_id,kind,amount,external_id) VALUES(?,?,?,?)", (user_id,kind,amount,external_id))
        await db.commit()

async def transaction_exists(external_id):
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT 1 FROM transactions WHERE external_id=?", (external_id,))
        return await cur.fetchone() is not None

async def get_referrer(user_id):
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT referrer_id FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None
