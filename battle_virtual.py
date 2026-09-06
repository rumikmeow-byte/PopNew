import hashlib
import secrets
import time

import aiosqlite


class VirtualBattle:
    """Non-redeemable public battle points only; never touches Stars or TON balances."""

    def __init__(self, db_name: str):
        self.db_name = db_name

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS virtual_battle_users (
                    user_id INTEGER PRIMARY KEY,
                    points INTEGER NOT NULL DEFAULT 1000
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS public_battles (
                    battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'waiting',
                    created_at INTEGER NOT NULL,
                    countdown_end INTEGER,
                    ended_at INTEGER,
                    winner_id INTEGER,
                    seed TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS public_battle_players (
                    battle_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    bet_points INTEGER NOT NULL,
                    joined_at INTEGER NOT NULL,
                    PRIMARY KEY (battle_id, user_id)
                )
                """
            )
            await db.commit()

    async def _ensure_round(self, db):
        async with db.execute(
            "SELECT battle_id, status FROM public_battles WHERE status IN ('waiting','active') ORDER BY battle_id DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
        if row:
            return row[0]
        seed = secrets.token_hex(32)
        commitment = hashlib.sha256(seed.encode()).hexdigest()
        now = int(time.time())
        cur = await db.execute(
            "INSERT INTO public_battles(status,created_at,seed,hash) VALUES ('waiting',?,?,?)",
            (now, seed, commitment),
        )
        await db.commit()
        return cur.lastrowid

    async def _resolve_if_due(self, db):
        now = int(time.time())
        async with db.execute(
            "SELECT battle_id,countdown_end,seed FROM public_battles WHERE status='active' AND countdown_end <= ? ORDER BY battle_id",
            (now,),
        ) as cur:
            due = await cur.fetchall()
        for battle_id, _, seed in due:
            async with db.execute(
                "SELECT user_id,bet_points FROM public_battle_players WHERE battle_id=? ORDER BY joined_at",
                (battle_id,),
            ) as cur:
                players = await cur.fetchall()
            total = sum(max(0, int(bet)) for _, bet in players)
            winner = None
            if total:
                ticket = int.from_bytes(hashlib.sha256(f"{seed}:{battle_id}".encode()).digest()[:8], "big") % total
                cursor = 0
                for user_id, bet in players:
                    cursor += max(0, int(bet))
                    if ticket < cursor:
                        winner = user_id
                        break
            if winner is not None:
                await db.execute(
                    "INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,1000)",
                    (winner,),
                )
                await db.execute(
                    "UPDATE virtual_battle_users SET points=points+? WHERE user_id=?",
                    (total, winner),
                )
            await db.execute(
                "UPDATE public_battles SET status='finished',ended_at=?,winner_id=? WHERE battle_id=? AND status='active'",
                (now, winner, battle_id),
            )
        if due:
            await db.commit()

    async def snapshot(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            battle_id = await self._ensure_round(db)
            async with db.execute(
                "SELECT status,created_at,countdown_end,winner_id,hash FROM public_battles WHERE battle_id=?",
                (battle_id,),
            ) as cur:
                battle = await cur.fetchone()
            async with db.execute(
                "SELECT user_id,bet_points FROM public_battle_players WHERE battle_id=? ORDER BY joined_at",
                (battle_id,),
            ) as cur:
                players = await cur.fetchall()
            await db.execute(
                "INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,1000)",
                (user_id,),
            )
            async with db.execute("SELECT points FROM virtual_battle_users WHERE user_id=?", (user_id,)) as cur:
                points = (await cur.fetchone())[0]
            await db.commit()
            total = sum(int(bet) for _, bet in players)
            return {
                "battle_id": battle_id,
                "status": battle[0],
                "created_at": battle[1],
                "countdown_end": battle[2],
                "winner_id": battle[3],
                "hash": battle[4],
                "points": points,
                "bank": total,
                "players": [
                    {
                        "user_id": uid,
                        "bet": int(bet),
                        "chance": round((int(bet) / total) * 100, 2) if total else 0,
                    }
                    for uid, bet in players
                ],
            }

    async def join(self, user_id: int, amount: int):
        amount = int(amount)
        if amount not in (25, 100, 500):
            return {"ok": False, "message": "Выбери 25, 100 или 500 виртуальных очков."}
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            battle_id = await self._ensure_round(db)
            async with db.execute("SELECT status,countdown_end FROM public_battles WHERE battle_id=?", (battle_id,)) as cur:
                status, countdown_end = await cur.fetchone()
            if status != "waiting":
                return {"ok": False, "message": "Раунд уже запущен. Следующий раунд появится автоматически."}
            await db.execute(
                "INSERT OR IGNORE INTO virtual_battle_users(user_id,points) VALUES (?,1000)",
                (user_id,),
            )
            async with db.execute("SELECT points FROM virtual_battle_users WHERE user_id=?", (user_id,)) as cur:
                points = (await cur.fetchone())[0]
            if points < amount:
                return {"ok": False, "message": "Недостаточно виртуальных очков."}
            async with db.execute("SELECT 1 FROM public_battle_players WHERE battle_id=? AND user_id=?", (battle_id, user_id)) as cur:
                if await cur.fetchone():
                    return {"ok": False, "message": "Ты уже в этом раунде."}
            now = int(time.time())
            await db.execute("UPDATE virtual_battle_users SET points=points-? WHERE user_id=?", (amount, user_id))
            await db.execute(
                "INSERT INTO public_battle_players(battle_id,user_id,bet_points,joined_at) VALUES (?,?,?,?)",
                (battle_id, user_id, amount, now),
            )
            async with db.execute("SELECT COUNT(*) FROM public_battle_players WHERE battle_id=?", (battle_id,)) as cur:
                count = (await cur.fetchone())[0]
            if count == 1:
                countdown_end = now + 10
                await db.execute("UPDATE public_battles SET status='active',countdown_end=? WHERE battle_id=?", (countdown_end, battle_id))
            await db.commit()
        return {"ok": True, "battle": await self.snapshot(user_id)}
