import hashlib
import secrets
import time

import aiosqlite


MIN_REAL_PLAYERS = 2
ROUND_WAIT_SECONDS = 15
STARS_TO_POINTS = 100
TON_TO_POINTS = 10000


class VirtualBattle:
    """Public arena using purchased virtual points; points are not cash and cannot be withdrawn."""

    def __init__(self, db_name: str):
        self.db_name = db_name

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS virtual_battle_users (user_id INTEGER PRIMARY KEY, points INTEGER NOT NULL DEFAULT 0)")
            await db.execute("""CREATE TABLE IF NOT EXISTS public_battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT NOT NULL DEFAULT 'waiting',
                created_at INTEGER NOT NULL, countdown_end INTEGER, ended_at INTEGER,
                winner_id INTEGER, seed TEXT NOT NULL, hash TEXT NOT NULL)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS public_battle_players (
                battle_id INTEGER NOT NULL, user_id INTEGER NOT NULL, bet_points INTEGER NOT NULL,
                display_name TEXT NOT NULL DEFAULT 'Игрок', joined_at INTEGER NOT NULL,
                PRIMARY KEY (battle_id, user_id))""")
            await self._ensure_column(db, "public_battle_players", "display_name", "TEXT NOT NULL DEFAULT 'Игрок'")
            await db.commit()

    @staticmethod
    async def _ensure_column(db, table: str, column: str, definition: str):
        async with db.execute(f"PRAGMA table_info({table})") as cur:
            columns = {row[1] for row in await cur.fetchall()}
        if column not in columns:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    async def credit_points(self, user_id: int, points: int):
        points = int(points)
        if points <= 0:
            return False
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (user_id,))
            await db.execute("UPDATE virtual_battle_users SET points=points+? WHERE user_id=?", (points, user_id))
            await db.commit()
        return True

    async def _sync_ton_funding(self, db, user_id: int):
        """Turn already-confirmed TON top-ups into non-cash virtual points once."""
        try:
            async with db.execute("SELECT ton_balance FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
            ton_balance = float(row[0] or 0) if row else 0.0
        except Exception:
            ton_balance = 0.0
        if ton_balance <= 0:
            return 0
        points = int(ton_balance * TON_TO_POINTS)
        if points <= 0:
            return 0
        await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (user_id,))
        await db.execute("UPDATE virtual_battle_users SET points=points+? WHERE user_id=?", (points, user_id))
        await db.execute("UPDATE users SET ton_balance=0 WHERE user_id=?", (user_id,))
        return points

    async def get_points(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (user_id,))
            await self._sync_ton_funding(db, user_id)
            async with db.execute("SELECT points FROM virtual_battle_users WHERE user_id=?", (user_id,)) as cur:
                points = int((await cur.fetchone())[0])
            await db.commit()
        return points

    async def _ensure_round(self, db):
        async with db.execute("SELECT battle_id,status FROM public_battles WHERE status IN ('waiting','active') ORDER BY battle_id DESC LIMIT 1") as cur:
            row = await cur.fetchone()
        if row:
            return row[0]
        now = int(time.time())
        seed = secrets.token_hex(32)
        commitment = hashlib.sha256(seed.encode()).hexdigest()
        cur = await db.execute(
            "INSERT INTO public_battles(status,created_at,countdown_end,seed,hash) VALUES ('waiting',?,?,?,?)",
            (now, now + ROUND_WAIT_SECONDS, seed, commitment),
        )
        await db.commit()
        return cur.lastrowid

    async def _resolve_if_due(self, db):
        now = int(time.time())
        async with db.execute("SELECT battle_id,countdown_end,seed FROM public_battles WHERE status='waiting' AND countdown_end <= ? ORDER BY battle_id", (now,)) as cur:
            waiting_due = await cur.fetchall()
        for battle_id, _, seed in waiting_due:
            async with db.execute("SELECT user_id,bet_points FROM public_battle_players WHERE battle_id=? ORDER BY joined_at", (battle_id,)) as cur:
                players = await cur.fetchall()
            if len(players) < MIN_REAL_PLAYERS:
                # No bots or AFK placeholders: an under-filled round simply expires.
                await db.execute("UPDATE public_battles SET status='finished',ended_at=? WHERE battle_id=? AND status='waiting'", (now, battle_id))
                continue
            await db.execute("UPDATE public_battles SET status='active',countdown_end=? WHERE battle_id=? AND status='waiting'", (now + 10, battle_id))

        async with db.execute("SELECT battle_id,countdown_end,seed FROM public_battles WHERE status='active' AND countdown_end <= ? ORDER BY battle_id", (now,)) as cur:
            active_due = await cur.fetchall()
        for battle_id, _, seed in active_due:
            async with db.execute("SELECT user_id,bet_points FROM public_battle_players WHERE battle_id=? ORDER BY joined_at", (battle_id,)) as cur:
                players = await cur.fetchall()
            if len(players) < MIN_REAL_PLAYERS:
                await db.execute("UPDATE public_battles SET status='finished',ended_at=? WHERE battle_id=? AND status='active'", (now, battle_id))
                continue
            total = sum(max(0, int(bet)) for _, bet in players)
            ticket = int.from_bytes(hashlib.sha256(f"{seed}:{battle_id}".encode()).digest()[:8], "big") % total if total else 0
            winner = None
            cursor = 0
            for user_id, bet in players:
                cursor += max(0, int(bet))
                if total and ticket < cursor:
                    winner = user_id
                    break
            if winner is not None:
                await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (winner,))
                await db.execute("UPDATE virtual_battle_users SET points=points+? WHERE user_id=?", (total, winner))
            await db.execute("UPDATE public_battles SET status='finished',ended_at=?,winner_id=? WHERE battle_id=? AND status='active'", (now, winner, battle_id))
        if waiting_due or active_due:
            await db.commit()

    async def snapshot(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (user_id,))
            await self._sync_ton_funding(db, user_id)
            battle_id = await self._ensure_round(db)
            async with db.execute("SELECT status,created_at,countdown_end,winner_id,hash FROM public_battles WHERE battle_id=?", (battle_id,)) as cur:
                battle = await cur.fetchone()
            async with db.execute("SELECT user_id,bet_points,display_name FROM public_battle_players WHERE battle_id=? ORDER BY joined_at", (battle_id,)) as cur:
                players = await cur.fetchall()
            async with db.execute("SELECT points FROM virtual_battle_users WHERE user_id=?", (user_id,)) as cur:
                points = int((await cur.fetchone())[0])
            await db.commit()
        total = sum(int(bet) for _, bet, _ in players)
        return {
            "battle_id": battle_id,
            "status": battle[0],
            "created_at": battle[1],
            "countdown_end": battle[2],
            "winner_id": battle[3],
            "hash": battle[4],
            "points": points,
            "bank": total,
            "min_players": MIN_REAL_PLAYERS,
            "players": [
                {"user_id": uid, "name": name, "bet": int(bet), "chance": round((int(bet) / total) * 100, 2) if total else 0}
                for uid, bet, name in players
            ],
        }

    async def join(self, user_id: int, amount: int, display_name: str = "Игрок"):
        amount = int(amount)
        if amount not in (25, 100, 500):
            return {"ok": False, "message": "Выбери 25, 100 или 500 виртуальных очков."}
        display_name = (display_name or "Игрок").strip()[:64] or "Игрок"
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (user_id,))
            await self._sync_ton_funding(db, user_id)
            battle_id = await self._ensure_round(db)
            async with db.execute("SELECT status FROM public_battles WHERE battle_id=?", (battle_id,)) as cur:
                status = (await cur.fetchone())[0]
            if status != "waiting":
                return {"ok": False, "message": "Раунд уже начался. Дождитесь следующего раунда."}
            async with db.execute("SELECT points FROM virtual_battle_users WHERE user_id=?", (user_id,)) as cur:
                points = int((await cur.fetchone())[0])
            if points < amount:
                return {"ok": False, "message": "Сначала пополните баланс Stars или TON, чтобы получить виртуальные очки."}
            async with db.execute("SELECT 1 FROM public_battle_players WHERE battle_id=? AND user_id=?", (battle_id, user_id)) as cur:
                if await cur.fetchone():
                    return {"ok": False, "message": "Ты уже в этом раунде."}
            now = int(time.time())
            await db.execute("UPDATE virtual_battle_users SET points=points-? WHERE user_id=?", (amount, user_id))
            await db.execute("INSERT INTO public_battle_players(battle_id,user_id,bet_points,display_name,joined_at) VALUES (?,?,?,?,?)", (battle_id, user_id, amount, display_name, now))
            await db.commit()
        return {"ok": True, "battle": await self.snapshot(user_id)}
