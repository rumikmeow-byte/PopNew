import aiosqlite
from config import settings

CURRENCIES = ("credits", "stars", "ton")


def _balance_column(currency: str) -> str:
    mapping = {"credits": "balance", "stars": "stars_balance", "ton": "ton_balance"}
    try:
        return mapping[currency]
    except KeyError:
        raise ValueError("Unsupported currency")


async def init_db():
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER NOT NULL DEFAULT 0,
            stars_balance INTEGER NOT NULL DEFAULT 0,
            ton_balance INTEGER NOT NULL DEFAULT 0,
            referrer_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stake INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'credits',
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
            currency TEXT NOT NULL DEFAULT 'credits',
            external_id TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        await _ensure_column(db, "users", "stars_balance", "INTEGER NOT NULL DEFAULT 0")
        await _ensure_column(db, "users", "ton_balance", "INTEGER NOT NULL DEFAULT 0")
        await _ensure_column(db, "games", "currency", "TEXT NOT NULL DEFAULT 'credits'")
        await _ensure_column(db, "transactions", "currency", "TEXT NOT NULL DEFAULT 'credits'")
        await db.commit()


async def _ensure_column(db, table: str, column: str, definition: str):
    cur = await db.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in await cur.fetchall()}
    if column not in columns:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


async def get_user(user_id):
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return await cur.fetchone()


async def create_user(user_id, username, referrer_id=None):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users(id,username,referrer_id) VALUES(?,?,?)",
            (user_id, username, referrer_id),
        )
        await db.commit()


async def change_balance(user_id, delta, currency="credits"):
    column = _balance_column(currency)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(f"UPDATE users SET {column}={column}+? WHERE id=?", (delta, user_id))
        await db.commit()


async def make_game(user_id, stake, chance, roll, coefficient, result, delta, currency="credits"):
    column = _balance_column(currency)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute(f"SELECT {column} FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        if not row or row[0] < stake:
            await db.rollback()
            return False
        await db.execute(f"UPDATE users SET {column}={column}+? WHERE id=?", (delta, user_id))
        await db.execute(
            "INSERT INTO games(user_id,stake,currency,chance,roll,coefficient,result,delta) VALUES(?,?,?,?,?,?,?,?)",
            (user_id, stake, currency, chance, roll, coefficient, result, delta),
        )
        await db.execute(
            "INSERT INTO transactions(user_id,kind,amount,currency,external_id) VALUES(?,?,?,?,?)",
            (user_id, "game", delta, currency, f"game:{currency}:{user_id}:{await _last_game_id(db)}"),
        )
        await db.commit()
        return True


async def _last_game_id(db):
    cur = await db.execute("SELECT last_insert_rowid()")
    row = await cur.fetchone()
    return row[0]


async def add_transaction(user_id, kind, amount, external_id, currency="credits"):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT INTO transactions(user_id,kind,amount,currency,external_id) VALUES(?,?,?,?,?)",
            (user_id, kind, amount, currency, external_id),
        )
        await db.commit()


async def transaction_exists(external_id):
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT 1 FROM transactions WHERE external_id=?", (external_id,))
        return await cur.fetchone() is not None


async def credit_external_payment(user_id, amount, currency, kind, external_id):
    if amount <= 0:
        raise ValueError("Payment amount must be positive")
    column = _balance_column(currency)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute("SELECT 1 FROM transactions WHERE external_id=?", (external_id,))
        if await cur.fetchone():
            await db.rollback()
            return False
        await db.execute(f"UPDATE users SET {column}={column}+? WHERE id=?", (amount, user_id))
        await db.execute(
            "INSERT INTO transactions(user_id,kind,amount,currency,external_id) VALUES(?,?,?,?,?)",
            (user_id, kind, amount, currency, external_id),
        )
        await db.commit()
        return True


async def get_referrer(user_id):
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT referrer_id FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None
