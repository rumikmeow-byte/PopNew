import random
import time
from urllib.parse import quote

import aiosqlite
from aiohttp import web


class MiniAppFeatures:
    def __init__(self, db_name, bot):
        self.db_name = db_name
        self.bot = bot

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS mini_users (user_id INTEGER PRIMARY KEY, tickets INTEGER DEFAULT 5)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, reward INTEGER NOT NULL, kind TEXT NOT NULL, url TEXT DEFAULT '')")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_task_claims (user_id INTEGER, task_id INTEGER, claimed_at INTEGER, PRIMARY KEY(user_id, task_id))")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, title TEXT, amount TEXT, created_at INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_contest_entries (contest_id INTEGER, user_id INTEGER, tickets INTEGER, created_at INTEGER, PRIMARY KEY(contest_id,user_id))")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_contests (contest_id INTEGER PRIMARY KEY, title TEXT, prize TEXT, entry_tickets INTEGER, ends_at INTEGER, active INTEGER DEFAULT 1)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_case_opens (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, case_id TEXT, reward TEXT, created_at INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_leaderboard (user_id INTEGER PRIMARY KEY, score INTEGER DEFAULT 0)")
            tasks = await db.execute("SELECT COUNT(*) FROM mini_tasks")
            if (await tasks.fetchone())[0] == 0:
                await db.executemany("INSERT INTO mini_tasks(title,reward,kind,url) VALUES(?,?,?,?)", [
                    ("Подпишись на GIFTSMMS News", 1, "subscribe", "https://t.me/Eclipsedlf"),
                    ("Поделись GIFTSMMS с другом", 5, "share", ""),
                    ("Открой Mini App", 2, "visit", ""),
                ])
            await db.commit()

    async def _user(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT OR IGNORE INTO mini_users(user_id,tickets) VALUES(?,5)", (user_id,))
            await db.execute("INSERT OR IGNORE INTO mini_leaderboard(user_id,score) VALUES(?,0)", (user_id,))
            await db.commit()
            async with db.execute("SELECT tickets FROM mini_users WHERE user_id=?", (user_id,)) as c:
                tickets = (await c.fetchone())[0]
        return tickets

    async def snapshot(self, user_id):
        tickets = await self._user(user_id)
        now = int(time.time())
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT task_id,title,reward,kind,url FROM mini_tasks ORDER BY task_id") as c:
                tasks = [{"id":r[0],"title":r[1],"reward":r[2],"kind":r[3],"url":r[4]} for r in await c.fetchall()]
            async with db.execute("SELECT task_id FROM mini_task_claims WHERE user_id=?", (user_id,)) as c:
                claimed = {r[0] for r in await c.fetchall()}
            async with db.execute("SELECT user_id,score FROM mini_leaderboard ORDER BY score DESC, user_id LIMIT 20") as c:
                leaders = [{"user_id":r[0],"score":r[1]} for r in await c.fetchall()]
            async with db.execute("SELECT id,kind,title,amount,created_at FROM mini_history WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,)) as c:
                history = [{"id":r[0],"kind":r[1],"title":r[2],"amount":r[3],"created_at":r[4]} for r in await c.fetchall()]
        return {"tickets":tickets,"tasks":tasks,"claimed_tasks":list(claimed),"contest":None,"leaders":leaders,"history":history,"case_history":[],"now":now}

    async def claim_task(self, user_id, task_id):
        await self._user(user_id)
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT title,reward,kind,url FROM mini_tasks WHERE task_id=?", (task_id,)) as c:
                task = await c.fetchone()
            if not task:
                return {"ok":False,"message":"Задание не найдено"}
            async with db.execute("SELECT 1 FROM mini_task_claims WHERE user_id=? AND task_id=?", (user_id,task_id)) as c:
                if await c.fetchone():
                    return {"ok":True,"already":True,"message":"Награда уже получена"}
            if task[2] == "subscribe":
                try:
                    member = await self.bot.get_chat_member("@Eclipsedlf", user_id)
                    if member.status not in ("member","administrator","creator"):
                        return {"ok":False,"message":"Сначала подпишитесь на @Eclipsedlf"}
                except Exception:
                    return {"ok":False,"message":"Не удалось проверить подписку. Попробуйте ещё раз."}
            await db.execute("INSERT INTO mini_task_claims VALUES(?,?,?)", (user_id,task_id,int(time.time())))
            await db.execute("UPDATE mini_users SET tickets=tickets+? WHERE user_id=?", (task[1],user_id))
            await db.execute("UPDATE mini_leaderboard SET score=score+? WHERE user_id=?", (task[1],user_id))
            await db.execute("INSERT INTO mini_history(user_id,kind,title,amount,created_at) VALUES(?,?,?,?,?)", (user_id,"task",task[0],f"+{task[1]} 🎫",int(time.time())))
            await db.commit()
        return {"ok":True,"reward":task[1],"message":"Награда получена ✅"}

    async def enter_contest(self, user_id):
        return {"ok":False,"message":"Конкурсы отключены."}

    async def open_case(self, user_id, case_id):
        await self._user(user_id)
        if case_id != "free":
            return {"ok":False,"message":"Доступен только бесплатный кейс."}
        reward = random.choice(["Telegram Gift — Common", "Rare Sticker", "Premium Gift"])
        now = int(time.time())
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO mini_case_opens(user_id,case_id,reward,created_at) VALUES(?,?,?,?)",(user_id,"free",reward,now))
            await db.execute("INSERT INTO mini_history(user_id,kind,title,amount,created_at) VALUES(?,?,?,?,?)",(user_id,"case","Бесплатный кейс",reward,now))
            await db.commit()
        return {"ok":True,"reward":reward}

    async def routes(self, app, auth):
        async def state(request):
            uid,_=auth(request); return web.json_response(await self.snapshot(uid))
        async def task(request):
            uid,_=auth(request); body=await request.json(); return web.json_response(await self.claim_task(uid,int(body.get("task_id",0))))
        async def contest(request):
            uid,_=auth(request); return web.json_response(await self.enter_contest(uid))
        async def case(request):
            uid,_=auth(request); body=await request.json(); return web.json_response(await self.open_case(uid,str(body.get("case_id",""))))
        async def share(request):
            uid,_=auth(request); return web.json_response({"ok":True,"share_url":f"https://t.me/share/url?url={quote('https://t.me/GIFTSMMS_bot')}&text={quote('Попробуй GIFTSMMS 🎁')}"})
        app.router.add_get("/api/mini/state",state)
        app.router.add_post("/api/mini/task/claim",task)
        app.router.add_post("/api/mini/contest/enter",contest)
        app.router.add_post("/api/mini/case/open",case)
        app.router.add_get("/api/mini/share",share)
