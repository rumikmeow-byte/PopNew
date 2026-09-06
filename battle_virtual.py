import hashlib
import secrets
import time

import aiosqlite

from config import ADMIN_ID


MIN_REAL_PLAYERS = 2
MAX_REAL_PLAYERS = 8
ROUND_WAIT_SECONDS = 15
ROUND_ACTIVE_SECONDS = 10
STARS_TO_POINTS = 100
TON_TO_POINTS = 10000
TEST_POINTS = 200


class VirtualBattle:
    """Public arena using virtual points; points are not cash and cannot be withdrawn."""

    def __init__(self, db_name: str):
        self.db_name = db_name

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS virtual_battle_users (user_id INTEGER PRIMARY KEY, points INTEGER NOT NULL DEFAULT 0)")
            await db.execute("CREATE TABLE IF NOT EXISTS virtual_test_grants (user_id INTEGER PRIMARY KEY, points INTEGER NOT NULL, granted_at INTEGER NOT NULL)")
            await db.execute("""CREATE TABLE IF NOT EXISTS public_battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT NOT NULL DEFAULT 'waiting',
                created_at INTEGER NOT NULL, countdown_end INTEGER, ended_at INTEGER,
                winner_id INTEGER, seed TEXT NOT NULL, hash TEXT NOT NULL)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS public_battle_players (
                battle_id INTEGER NOT NULL, user_id INTEGER NOT NULL, bet_points INTEGER NOT NULL,
                display_name TEXT NOT NULL DEFAULT 'Игрок', joined_at INTEGER NOT NULL,
                PRIMARY KEY (battle_id, user_id))""")
            await self._ensure_column(db, "public_battle_players", "display_name", "TEXT NOT NULL DEFAULT 'Игрок'")

            if ADMIN_ID:
                async with db.execute("SELECT 1 FROM virtual_test_grants WHERE user_id=?", (ADMIN_ID,)) as cur:
                    already_granted = await cur.fetchone()
                if not already_granted:
                    await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (ADMIN_ID,))
                    await db.execute("UPDATE virtual_battle_users SET points=points+? WHERE user_id=?", (TEST_POINTS, ADMIN_ID))
                    await db.execute("INSERT INTO virtual_test_grants(user_id,points,granted_at) VALUES (?,?,?)", (ADMIN_ID, TEST_POINTS, int(time.time())))
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
                await db.execute("UPDATE public_battles SET status='finished',ended_at=? WHERE battle_id=? AND status='waiting'", (now, battle_id))
                continue
            await db.execute("UPDATE public_battles SET status='active',countdown_end=? WHERE battle_id=? AND status='waiting'", (now + ROUND_ACTIVE_SECONDS, battle_id))

        async with db.execute("SELECT battle_id,countdown_end,seed FROM public_battles WHERE status='active' AND countdown_end <= ? ORDER BY battle_id", (now,)) as cur:
            active_due = await cur.fetchall()
        for battle_id, _, seed in active_due:
            async with db.execute("SELECT user_id,bet_points FROM public_battle_players WHERE battle_id=? ORDER BY joined_at", (battle_id,)) as cur:
                players = await cur.fetchall()
            if len(players) < MIN_REAL_PLAYERS:
                await db.execute("UPDATE public_battles SET status='finished',ended_at=?,winner_id=? WHERE battle_id=? AND status='active'", (now, None, battle_id))
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
            async with db.execute("""SELECT battle_id,created_at,ended_at,winner_id,hash
                                      FROM public_battles
                                      WHERE status='finished' AND battle_id IN
                                      (SELECT battle_id FROM public_battle_players WHERE user_id=?)
                                      ORDER BY battle_id DESC LIMIT 20""", (user_id,)) as cur:
                history_rows = await cur.fetchall()
            history = []
            for hid, created_at, ended_at, winner_id, hsh in history_rows:
                async with db.execute("SELECT user_id,display_name,bet_points FROM public_battle_players WHERE battle_id=? ORDER BY joined_at", (hid,)) as cur:
                    hplayers = await cur.fetchall()
                total_h = sum(int(p[2]) for p in hplayers)
                history.append({
                    "battle_id": hid,
                    "created_at": created_at,
                    "ended_at": ended_at,
                    "winner_id": winner_id,
                    "bank": total_h,
                    "result": "win" if winner_id == user_id else "loss" if winner_id else "void",
                    "hash": hsh,
                    "players": [{"user_id": p[0], "name": p[1], "bet": int(p[2])} for p in hplayers],
                })
            await db.commit()
        total = sum(int(bet) for _, bet, _ in players)
        return {
            "server_time": int(time.time()),
            "battle_id": battle_id,
            "room_type": "free",
            "visibility": "public",
            "status": battle[0],
            "created_at": battle[1],
            "countdown_end": battle[2],
            "winner_id": battle[3],
            "hash": battle[4],
            "points": points,
            "bank": total,
            "min_players": MIN_REAL_PLAYERS,
            "max_players": MAX_REAL_PLAYERS,
            "entry_options": [25, 100, 500],
            "players": [
                {"user_id": uid, "name": name, "bet": int(bet), "chance": round((int(bet) / total) * 100, 2) if total else 0}
                for uid, bet, name in players
            ],
            "history": history,
        }

    async def join(self, user_id: int, amount: int, display_name: str = "Игрок"):
        amount = int(amount)
        if amount not in (25, 100, 500):
            return {"ok": False, "message": "Выбери 25, 100 или 500 виртуальных очков."}
        display_name = (display_name or "Игрок").strip()[:64] or "Игрок"
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,0)", (user_id,))
            await self._sync_ton_funding(db, user_id)
            battle_id = await self._ensure_round(db)
            async with db.execute("SELECT status FROM public_battles WHERE battle_id=?", (battle_id,)) as cur:
                status = (await cur.fetchone())[0]
            if status != "waiting":
                await db.rollback()
                return {"ok": False, "message": "Раунд уже начался. Дождитесь следующего раунда."}
            async with db.execute("SELECT COUNT(*) FROM public_battle_players WHERE battle_id=?", (battle_id,)) as cur:
                player_count = int((await cur.fetchone())[0])
            if player_count >= MAX_REAL_PLAYERS:
                await db.rollback()
                return {"ok": False, "message": "Арена уже заполнена. Дождитесь следующего раунда."}
            async with db.execute("SELECT points FROM virtual_battle_users WHERE user_id=?", (user_id,)) as cur:
                points = int((await cur.fetchone())[0])
            if points < amount:
                await db.rollback()
                return {"ok": False, "message": "Недостаточно виртуальных очков. Пополните баланс через доступные способы."}
            async with db.execute("SELECT 1 FROM public_battle_players WHERE battle_id=? AND user_id=?", (battle_id, user_id)) as cur:
                if await cur.fetchone():
                    await db.rollback()
                    return {"ok": False, "message": "Ты уже в этом раунде."}
            now = int(time.time())
            await db.execute("UPDATE virtual_battle_users SET points=points-? WHERE user_id=? AND points>=?", (amount, user_id, amount))
            if db.total_changes < 1:
                await db.rollback()
                return {"ok": False, "message": "Не удалось зарезервировать виртуальные очки. Повтори попытку."}
            await db.execute("INSERT INTO public_battle_players(battle_id,user_id,bet_points,display_name,joined_at) VALUES (?,?,?,?,?)", (battle_id, user_id, amount, display_name, now))
            new_count = player_count + 1
            if new_count >= MAX_REAL_PLAYERS:
                await db.execute("UPDATE public_battles SET countdown_end=MIN(countdown_end,?) WHERE battle_id=? AND status='waiting'", (now + 3, battle_id))
            await db.commit()
        return {"ok": True, "battle": await self.snapshot(user_id)}
