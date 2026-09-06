import hashlib
import math
import secrets
import time

import aiosqlite
from aiohttp import web

from config import MIN_DEPOSIT_STARS


async def init_crash_db(db_name: str):
    async with aiosqlite.connect(db_name) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS crash_rounds (
            round_id INTEGER PRIMARY KEY AUTOINCREMENT, seed TEXT NOT NULL, seed_hash TEXT NOT NULL,
            crash_at REAL NOT NULL, started_at REAL NOT NULL, crashed_at REAL DEFAULT NULL,
            status TEXT DEFAULT 'waiting')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS crash_bets (
            bet_id INTEGER PRIMARY KEY AUTOINCREMENT, round_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            stake INTEGER NOT NULL, payout INTEGER DEFAULT 0, multiplier REAL DEFAULT NULL,
            status TEXT DEFAULT 'active', created_at REAL NOT NULL, cashed_at REAL DEFAULT NULL,
            UNIQUE(round_id, user_id))""")
        await db.commit()


def _crash_point(seed: str) -> float:
    digest = hashlib.sha256(seed.encode()).digest()
    n = int.from_bytes(digest[:8], "big")
    u = (n + 1) / float(2**64)
    point = 1.0 / max(0.02, 1.0 - u)
    return round(max(1.01, min(50.0, point)), 2)


def _multiplier(started_at: float, now: float) -> float:
    return round(min(50.0, math.exp(max(0.0, now - started_at) / 9.0)), 2)


async def _ensure_round(db_name: str):
    now = time.time()
    async with aiosqlite.connect(db_name) as db:
        async with db.execute("SELECT round_id,seed,seed_hash,crash_at,started_at,crashed_at,status FROM crash_rounds ORDER BY round_id DESC LIMIT 1") as cur:
            row = await cur.fetchone()
        if row:
            round_id, seed, seed_hash, crash_at, started_at, crashed_at, status = row
            if status == "running":
                current = _multiplier(started_at, now)
                if current >= crash_at:
                    await db.execute("UPDATE crash_rounds SET status='crashed',crashed_at=? WHERE round_id=? AND status='running'", (now, round_id))
                    await db.execute("UPDATE crash_bets SET status='lost' WHERE round_id=? AND status='active'", (round_id,))
                    await db.commit()
                    return (round_id, seed, seed_hash, crash_at, started_at, now, "crashed")
                return row
            if status == "crashed" and crashed_at and now - crashed_at < 2.5:
                return row
        seed = secrets.token_hex(32)
        seed_hash = hashlib.sha256(seed.encode()).hexdigest()
        cur = await db.execute("INSERT INTO crash_rounds(seed,seed_hash,crash_at,started_at,status) VALUES(?,?,?,?, 'waiting')", (seed, seed_hash, _crash_point(seed), 0.0))
        round_id = cur.lastrowid
        await db.commit()
        return (round_id, seed, seed_hash, _crash_point(seed), 0.0, None, "waiting")


async def crash_state(db_name: str, user_id: int):
    row = await _ensure_round(db_name)
    round_id, seed, seed_hash, crash_at, started_at, crashed_at, status = row
    now = time.time()
    multiplier = min(crash_at, _multiplier(started_at, now)) if status == "running" else (crash_at if status == "crashed" else 1.0)
    async with aiosqlite.connect(db_name) as db:
        async with db.execute("SELECT bet_id,stake,payout,multiplier,status FROM crash_bets WHERE round_id=? AND user_id=?", (round_id, user_id)) as cur:
            bet = await cur.fetchone()
    return {"round_id": round_id, "status": status, "multiplier": multiplier, "crash_at": crash_at if status == "crashed" else None, "seed_hash": seed_hash, "server_seed": seed if status == "crashed" else None, "bet": {"bet_id": bet[0],"stake": bet[1],"payout": bet[2],"multiplier": bet[3],"status": bet[4]} if bet else None}


async def place_crash_bet(db_name: str, user_id: int, stake: int):
    if stake < MIN_DEPOSIT_STARS:
        return False, f"Минимальная ставка — {MIN_DEPOSIT_STARS} ⭐."
    row = await _ensure_round(db_name)
    round_id, seed, seed_hash, crash_at, _, _, status = row
    async with aiosqlite.connect(db_name) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT status FROM crash_rounds WHERE round_id=?", (round_id,)) as cur:
            current_status = (await cur.fetchone())[0]
        if current_status != "waiting":
            await db.rollback()
            return False, "Раунд уже запущен."
        async with db.execute("SELECT 1 FROM crash_bets WHERE round_id=? AND user_id=?", (round_id, user_id)) as cur:
            if await cur.fetchone():
                await db.rollback()
                return False, "У вас уже есть ставка в этом раунде."
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)) as cur:
            row_user = await cur.fetchone()
        if not row_user or float(row_user[0] or 0) < stake:
            await db.rollback()
            return False, "Недостаточно ⭐."
        now = time.time()
        await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (stake, user_id))
        await db.execute("INSERT INTO crash_bets(round_id,user_id,stake,created_at) VALUES(?,?,?,?)", (round_id, user_id, stake, now))
        await db.execute("UPDATE crash_rounds SET status='running',started_at=? WHERE round_id=? AND status='waiting'", (now, round_id))
        await db.commit()
    return True, "Ставка принята"


async def cashout_crash_bet(db_name: str, user_id: int):
    row = await _ensure_round(db_name)
    round_id, _, _, crash_at, started_at, _, status = row
    now = time.time()
    multiplier = min(crash_at, _multiplier(started_at, now))
    if status != "running" or multiplier >= crash_at:
        return False, "Раунд уже завершён.", 0
    async with aiosqlite.connect(db_name) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT bet_id,stake,status FROM crash_bets WHERE round_id=? AND user_id=?", (round_id, user_id)) as cur:
            bet = await cur.fetchone()
        if not bet or bet[2] != "active":
            await db.rollback()
            return False, "Активная ставка не найдена.", 0
        payout = max(1, int(bet[1] * multiplier))
        changed = await db.execute("UPDATE crash_bets SET status='cashed',payout=?,multiplier=?,cashed_at=? WHERE bet_id=? AND status='active'", (payout, multiplier, now, bet[0]))
        if changed.rowcount != 1:
            await db.rollback()
            return False, "Ставка уже обработана.", 0
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (payout, user_id))
        await db.commit()
    return True, f"Вы забрали {payout} ⭐ на x{multiplier:.2f}", payout


def register_crash_routes(app: web.Application, db_name: str, validator):
    async def state(request):
        user_id, _ = validator(request)
        return web.json_response(await crash_state(db_name, user_id))
    async def bet(request):
        user_id, _ = validator(request)
        body = await request.json()
        try: stake = int(body.get("amount", 0))
        except (TypeError, ValueError): stake = 0
        ok, message = await place_crash_bet(db_name, user_id, stake)
        return web.json_response({"ok": ok, "message": message})
    async def cashout(request):
        user_id, _ = validator(request)
        ok, message, payout = await cashout_crash_bet(db_name, user_id)
        return web.json_response({"ok": ok, "message": message, "payout": payout})
    app.router.add_get("/api/crash/state", state)
    app.router.add_post("/api/crash/bet", bet)
    app.router.add_post("/api/crash/cashout", cashout)
