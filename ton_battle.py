import hashlib
import secrets
import time

import aiosqlite

from db import update_ton_balance


class TonBattle:
    def __init__(self, db_name: str):
        self.db_name = db_name

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ton_public_battles (
                    battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'waiting',
                    created_at INTEGER NOT NULL,
                    countdown_end INTEGER,
                    ended_at INTEGER,
                    winner_id INTEGER,
                    seed TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ton_public_battle_players (
                    battle_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    bet_ton REAL NOT NULL,
                    joined_at INTEGER NOT NULL,
                    PRIMARY KEY (battle_id, user_id)
                )
            """)
            await db.commit()

    async def _ensure_round(self, db):
        async with db.execute("SELECT battle_id FROM ton_public_battles WHERE status IN ('waiting','active') ORDER BY battle_id DESC LIMIT 1") as cur:
            row = await cur.fetchone()
        if row:
            return row[0]
        seed = secrets.token_hex(32)
        commitment = hashlib.sha256(seed.encode()).hexdigest()
        cur = await db.execute(
            "INSERT INTO ton_public_battles(status,created_at,seed,hash) VALUES ('waiting',?,?,?)",
            (int(time.time()), seed, commitment),
        )
        await db.commit()
        return cur.lastrowid

    async def _resolve_if_due(self, db):
        now = int(time.time())
        async with db.execute("SELECT battle_id,seed FROM ton_public_battles WHERE status='active' AND countdown_end<=? ORDER BY battle_id", (now,)) as cur:
            due = await cur.fetchall()
        for battle_id, seed in due:
            async with db.execute("SELECT user_id,bet_ton FROM ton_public_battle_players WHERE battle_id=? ORDER BY joined_at", (battle_id,)) as cur:
                players = await cur.fetchall()
            total = sum(max(0.0, float(bet)) for _, bet in players)
            winner = None
            if total > 0:
                # Use nanoton precision to make the weighted draw deterministic and auditable.
                weights = [(uid, int(round(max(0.0, float(bet)) * 1_000_000_000))) for uid, bet in players]
                total_nano = sum(w for _, w in weights)
                ticket = int.from_bytes(hashlib.sha256(f"{seed}:{battle_id}".encode()).digest()[:8], "big") % total_nano
                cursor = 0
                for uid, weight in weights:
                    cursor += weight
                    if ticket < cursor:
                        winner = uid
                        break
            if winner is not None and total > 0:
                await update_ton_balance(winner, total)
            await db.execute("UPDATE ton_public_battles SET status='finished',ended_at=?,winner_id=? WHERE battle_id=? AND status='active'", (now, winner, battle_id))
        if due:
            await db.commit()

    async def snapshot(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            battle_id = await self._ensure_round(db)
            async with db.execute("SELECT status,created_at,countdown_end,winner_id,hash FROM ton_public_battles WHERE battle_id=?", (battle_id,)) as cur:
                battle = await cur.fetchone()
            async with db.execute("SELECT user_id,bet_ton FROM ton_public_battle_players WHERE battle_id=? ORDER BY joined_at", (battle_id,)) as cur:
                players = await cur.fetchall()
            total = sum(float(bet) for _, bet in players)
            return {
                "battle_id": battle_id,
                "currency": "TON",
                "status": battle[0],
                "created_at": battle[1],
                "countdown_end": battle[2],
                "winner_id": battle[3],
                "hash": battle[4],
                "bank": round(total, 6),
                "players": [
                    {"user_id": uid, "bet": round(float(bet), 6), "chance": round((float(bet) / total) * 100, 2) if total else 0}
                    for uid, bet in players
                ],
            }

    async def join(self, user_id: int, amount: float):
        try:
            amount = round(float(amount), 6)
        except (TypeError, ValueError):
            return {"ok": False, "message": "Некорректная сумма TON."}
        if amount not in (0.1, 0.25, 0.5, 1.0):
            return {"ok": False, "message": "Выбери 0.1, 0.25, 0.5 или 1 TON."}
        async with aiosqlite.connect(self.db_name) as db:
            await self._resolve_if_due(db)
            battle_id = await self._ensure_round(db)
            async with db.execute("SELECT status FROM ton_public_battles WHERE battle_id=?", (battle_id,)) as cur:
                row = await cur.fetchone()
            if not row or row[0] != "waiting":
                return {"ok": False, "message": "Раунд уже запущен. Следующий появится автоматически."}
            async with db.execute("SELECT 1 FROM ton_public_battle_players WHERE battle_id=? AND user_id=?", (battle_id, user_id)) as cur:
                if await cur.fetchone():
                    return {"ok": False, "message": "Ты уже в этом TON-раунде."}
            async with db.execute("SELECT ton_balance FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
            balance = float(row[0] or 0) if row else 0.0
            if balance + 1e-9 < amount:
                return {"ok": False, "message": "Недостаточно TON. Пополни баланс."}
            now = int(time.time())
            # The balance and player record are changed in one SQLite transaction.
            await db.execute("UPDATE users SET ton_balance=ton_balance-? WHERE user_id=? AND ton_balance>=?", (amount, user_id, amount))
            async with db.execute("SELECT changes()") as cur:
                changed = (await cur.fetchone())[0]
            if changed != 1:
                return {"ok": False, "message": "Баланс TON изменился. Попробуй ещё раз."}
            await db.execute("INSERT INTO ton_public_battle_players(battle_id,user_id,bet_ton,joined_at) VALUES (?,?,?,?)", (battle_id, user_id, amount, now))
            async with db.execute("SELECT COUNT(*) FROM ton_public_battle_players WHERE battle_id=?", (battle_id,)) as cur:
                count = (await cur.fetchone())[0]
            if count == 1:
                await db.execute("UPDATE ton_public_battles SET status='active',countdown_end=? WHERE battle_id=?", (now + 10, battle_id))
            await db.commit()
        return {"ok": True, "battle": await self.snapshot(user_id)}
